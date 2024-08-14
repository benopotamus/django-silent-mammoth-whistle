from django.db.models import Count, Min, Max, F, CharField
from django.db.models.functions import Concat
from django.views.decorators.http import require_http_methods
from django.template.response import TemplateResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.utils.dateformat import format as format_date
from django.utils import timezone
from datetime import date, datetime, timedelta

from .models import *
from .forms import *


def get_start_end_dates(year, month):
	# Calculate the first day of the month
	start_date = date(year, month, 1)
	# Calculate the last day of the month
	if month == 12:
		end_date = date(year + 1, 1, 1) - timedelta(days=1)
	else:
		end_date = date(year, month + 1, 1) - timedelta(days=1)
	return start_date, end_date

def adjust_month(date, direction):
	'''
	Returns a date that is the 1st of the month.

	Direction can be "next", which increases the month by 1, or "previous": which reduces the month by 1
	'''
	if direction == "next":
		new_month = date.month + 1
		new_year = date.year
		if new_month > 12:
			new_month = 1
			new_year += 1
	elif direction == "previous":
		new_month = date.month - 1
		new_year = date.year
		if new_month < 1:
			new_month = 12
			new_year -= 1
	else:
		raise ValueError("The direction parameter must be 'next' or 'previous'")
	# Create the new date string in the format yyyy-mm-01
	result_date_str = f"{new_year:04d}-{new_month:02d}-01"
	return result_date_str

def adjust_day(date, direction):
    '''
	Returns a date that is one day forward or backwards in time.

	Direction can be "next", which increases the day by 1, or "previous": which reduces the day by 1
	'''
    if direction == "next":
        adjusted_date = date + timedelta(days=1)
    elif direction == "previous":
        adjusted_date = date - timedelta(days=1)
    else:
        raise ValueError("The direction parameter must be 'next' or 'previous'")
    result_date_str = adjusted_date.strftime("%Y-%m-%d")
    return result_date_str

# def is_bot(ua_string):
# 	'''
# 	Returns true if user agent string looks like a bot

# 	Copied from shynet/analytics/tasks.py
# 	'''
# 	return (
# 		ua_string.is_bot
# 		or (ua_string.browser.family or "").strip().lower() == "googlebot"
# 		or (ua_string.device.family or ua_string.device.model or "").strip().lower() == "spider"
# 	)


def create_chart_data(is_authenticated, requested_date):
	'''
	Returns data, labels, and dates for the bar chart displayed on the index page
	This function exists because roughly the same code needs to be called twice - once for authed and once for unauthed. It also makes the index view easier to read.
	'''
	# Get number of unique users per day during the month
	data = Whistle.objects.filter(
		is_authenticated=is_authenticated, # Using only authenticated sessions because the site gets so many unauthenticated spam sessions that it's not representative of user activity if unauthenticated is included
		datetime__year=requested_date.year, 
		datetime__month=requested_date.month
	).values('datetime__date') \
	.annotate(num_sessions=Count('user_id', distinct=True)) \
	.order_by('datetime__date')

	# Expand the above data so that each day either has the DB data above, or an entry of 0 for that day
	start_date, end_date = get_start_end_dates(requested_date.year, requested_date.month)
	dates_with_data = {entry['datetime__date'] for entry in data}

	chart_xaxis_labels = []
	chart_data = []
	chart_dates = []

	# Iterate over a range of dates between start and end dates
	current_date = start_date
	while current_date <= end_date:
		chart_dates.append(str(current_date))
		chart_xaxis_labels.append(current_date.day)

		if current_date in dates_with_data:
			entry = next(entry for entry in data if entry['datetime__date'] == current_date)
			chart_data.append(entry['num_sessions'])
		else:
			chart_data.append(0)

		# Move to the next date
		current_date += timedelta(days=1)

	return chart_data, chart_xaxis_labels, chart_dates


@require_http_methods(["GET"])
@staff_member_required
def index(request, requested_date=None):
	'''
	The homepage of silent_mammoth_whistle. It displays the days sessions, and a graph of the month's unique sessions

	requested_date should be of the form '2019-12-04'
	'''

	# Work out (from url parameter) which day is being requested
	if requested_date is None:
		requested_date = date.today()
	else:
		requested_date = date.fromisoformat(requested_date)
	
	authed_chart_data, chart_xaxis_labels, chart_dates = create_chart_data(True, requested_date)
	unauthed_chart_data = create_chart_data(False, requested_date)[0]

	
	# For the selected day,
	#	For each user that has 1 or more whistles that day
	#		get the count of the whistles
	#		get the time of the earliest whistle, and the latest whistle
	authed_whistles_per_user = Whistle.objects.filter(is_authenticated=True, datetime__date=requested_date).values('user_id', 'datetime__date').annotate(num_whistles=Count("user_id"), min_time=Min('datetime'), max_time=Max('datetime')).order_by('-max_time')

	unauthed_whistles_per_user = Whistle.objects.filter(is_authenticated=False, datetime__date=requested_date).values('user_id', 'datetime__date').annotate(num_whistles=Count("user_id"), min_time=Min('datetime'), max_time=Max('datetime')).order_by('-num_whistles')

	# Top platform (browser, device, etc), and viewport dimensions
	# These are per user in the given month. So if a user always has the same useragent, that will count as one. If they have 2 user agents in the month, that counts as 2. This is achieved by grouping the worthy whistles by useragent/viewport, and then counting the number of users who had that useragent/viewport.
	# Programming note: values() groups the queryset by the value, and an annotate count can be on any field (not just values() ones)

	worthy_useragents = Whistle.objects\
		.exclude(useragent='')\
		.filter(is_authenticated=True, datetime__year=requested_date.year, datetime__month=requested_date.month)\
		.values('datetime__date', 'user_id', 'useragent')\
		.distinct()\
		.annotate(user_and_date=Concat(F('datetime__date') ,F('user_id'), output_field=CharField()))
	top_useragents = worthy_useragents\
		.values('useragent')\
		.annotate(sessions=Count('user_and_date', distinct=True))\
		.order_by('-sessions')[:5]
	total_useragents = worthy_useragents.values('user_and_date').count()
	
	worthy_viewports = Whistle.objects\
		.exclude(viewport_dimensions='')\
		.filter(is_authenticated=True, datetime__year=requested_date.year, datetime__month=requested_date.month)\
		.values('datetime__date', 'user_id', 'viewport_dimensions')\
		.distinct()\
		.annotate(user_and_date=Concat(F('datetime__date') ,F('user_id'), output_field=CharField()))
	top_viewport_dimensions = worthy_viewports\
		.values('viewport_dimensions')\
		.annotate(sessions=Count('user_and_date', distinct=True))\
		.order_by('-sessions')[:5]
	total_viewport_dimensions = worthy_viewports.values('user_and_date').count()

	# Get a list of new users for the month
	new_users = get_user_model().objects.filter(is_superuser=False, last_login__isnull=False, date_joined__year=requested_date.year, date_joined__month=requested_date.month).order_by('date_joined')

	return TemplateResponse(request, 'silent_mammoth_whistle/index.html', {
		'date': requested_date,
		'day_str': format_date(requested_date, "l jS"),
		'day': requested_date.day-1,
		'chart_period': requested_date.strftime("%B %Y"),
		'chart_dates': chart_dates,
		'chart_xaxis_labels': chart_xaxis_labels,
		'authed_chart_data': authed_chart_data,
		'unauthed_chart_data': unauthed_chart_data,
		'authed_whistles_per_user': authed_whistles_per_user,
		'unauthed_whistles_per_user': unauthed_whistles_per_user,
		'month_has_whistles': any(authed_chart_data + unauthed_chart_data),
		'next_month': adjust_month(requested_date, 'next'),
		'previous_month': adjust_month(requested_date, 'previous'),
		'next_day': adjust_day(requested_date, 'next'),
		'previous_day': adjust_day(requested_date, 'previous'),
		'top_useragents': top_useragents,
		'total_useragents': total_useragents,
		'top_viewport_dimensions': top_viewport_dimensions,
		'total_viewport_dimensions': total_viewport_dimensions,
		'new_users': new_users,
	})

@require_http_methods(["GET"])
@staff_member_required
def session(request, user_id, requested_date):
	'''
	Displays a table of all the whistles for the given user and date
	'''
	requested_date_with_tz = timezone.make_aware(datetime.fromisoformat(requested_date))
	requested_date = date.fromisoformat(requested_date)
	whistles = Whistle.objects.filter(datetime__date=requested_date_with_tz, user_id=user_id).order_by('datetime')
	min_time = whistles.first().datetime
	max_time = whistles.last().datetime

	return TemplateResponse(request, 'silent_mammoth_whistle/session.html', {
		'user_id': user_id,
		'date': requested_date,
		'date_str': requested_date.strftime("%A %d %B %Y"),
		'whistles': whistles,
		'min_time': min_time,
		'max_time': max_time,
		'useragent': whistles.first().useragent,
		'viewport_dimensions': getattr(whistles.exclude(viewport_dimensions='').first(), 'viewport_dimensions', ''),
		'is_authenticated': whistles.first().is_authenticated,
	})
