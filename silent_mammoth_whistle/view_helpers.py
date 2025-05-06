from django.db.models.functions import TruncDate
from django.db.models import Count, OuterRef, Exists
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Whistle

User = get_user_model()
USER_ID_FIELD = getattr(settings, 'WHISTLE_USER_ID_FIELD', 'id')

def users_for_month(year, month):
	sessions = (
		Whistle.objects
		.filter(
			is_authenticated=True,
			datetime__year=year,
			datetime__month=month
		)
		.exclude(request='PING')
		.annotate(whistle_date=TruncDate('datetime'))
		.values('user_id')
		.annotate(sessions=Count('whistle_date', distinct=True))
		.order_by('-sessions')
	)

	# Reformat for template
	d = []
	for session in sessions:

		# This date joined query is a bit problematic because silent mammoth whistle doesn't force uniqueness of the user_id field
		# This code assumes the user_id value is unique. We might improve it in the future. 
		# E.g.
		#	user_objs = User.objects.in_bulk([session['user_id'] for session in sessions], field_name=USER_ID_FIELD)
		#	user = user_objs.get(session['user_id'])
		# 	is_new = (user.date_joined.year == year and user.date_joined.month == month) if user else False
		is_new = False
		try:
			User.objects.get(**{
				USER_ID_FIELD: session['user_id'],
				'date_joined__year': year, 
				'date_joined__month': month })
			is_new = True
		except User.DoesNotExist:
			pass
		except User.MultipleObjectsReturned:
			pass

		d.append({
			'user_id': session['user_id'],
			'sessions': session['sessions'],
			'is_new': is_new,
		})

	return d


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
	'''Returns a date that is the 1st of the month.

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
	'''Returns a date that is one day forward or backwards in time.

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


# This subquery is used when creating data for charts (create_chart_data) and for sessions themselves.
# It's used to check if any Whistle in the session is a 'PING'. Most malicious bots don't seem to execute the JavaScript that sends the 'PING' request
# Some good bots (like Google Bot and BingBot) do execute the 'PING' request so we just filter for 'bot' useragents as well
nonbot_whistles_query = (
	Whistle.objects
	.filter(user_id=OuterRef('user_id'), request='PING')
	.exclude(useragent__icontains='bot')
	.exclude(useragent__contains='HeadlessChrome')
)

def create_chart_data(is_authenticated, requested_date):
	'''Returns data, labels, and dates for the bar chart displayed on the index page
	This function exists because roughly the same code needs to be called twice - once for authed and once for unauthed. It also makes the index view easier to read.
	'''
	# Get number of unique users per day during the month
	data = (
		Whistle.objects
		.filter(
			is_authenticated=is_authenticated,
			datetime__year=requested_date.year, 
			datetime__month=requested_date.month)
		.exclude(request='PING')
		.values('datetime__date')
		.annotate(
			num_sessions=Count('user_id', distinct=True), 
			nonbot=Exists(nonbot_whistles_query))
		.filter(nonbot=True)
		.order_by('datetime__date')
	)

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


def get_user_sessions_chart_data(sessions):
    # Extract min/max date
    if sessions.exists():
        min_date = sessions.first()['min_time'].date()
        max_date = sessions.last()['min_time'].date()
    else:
        return [], []  # No data, return empty lists

    # Create a full date range dictionary with default values
    date_range = {min_date + timedelta(days=i): 0 for i in range((max_date - min_date).days + 1)}

    # Populate dictionary with actual data
    for session in sessions:
        session_date = session['min_time'].date()
        date_range[session_date] = session['num_whistles']

    # Convert to lists for Chart.js
    labels = [d.strftime('%Y-%m-%d') for d in date_range.keys()]
    data_values = list(date_range.values())

    return labels, data_values