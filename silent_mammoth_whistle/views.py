from django.conf import settings
from django.db.models import Count, Min, Max, F, CharField, Exists, Case, When, IntegerField
from django.db.models.functions import Concat
from django.views.decorators.http import require_http_methods
from django.template.response import TemplateResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.dateformat import format as format_date
from django.utils import timezone
from datetime import date, datetime

try:
	from invitations.utils import get_invitation_model
	Invitation = get_invitation_model()
except ModuleNotFoundError:
	Invitation = None

from . import view_helpers
from .models import Whistle


@require_http_methods(["GET"])
@staff_member_required
def index(request, requested_date=None):
	'''The homepage of silent_mammoth_whistle. It displays the days sessions, and a graph of the month's unique sessions.

	requested_date should be of the form '2019-12-04'
	'''

	# Work out (from url parameter) which day is being requested
	if requested_date is None:
		requested_date = date.today()
	else:
		requested_date = date.fromisoformat(requested_date)
	
	authed_chart_data, chart_xaxis_labels, chart_dates = view_helpers.create_chart_data(True, requested_date)
	unauthed_chart_data = view_helpers.create_chart_data(False, requested_date)[0]


	# Get the list of unique status codes for 4xx and 5xx responses.
	status_codes = Whistle.objects.filter(
		is_authenticated=True,
		datetime__date=requested_date,
		response_code__gte=400
	).exclude(request='PING').values_list('response_code', flat=True).distinct()

	# Build annotations for each status code.
	status_code_annotations = {
		f'count_{code}': Count(
			Case(
				When(response_code=code, then=1),
				output_field=IntegerField()
			)
		)
		for code in status_codes
	}


	# For the selected day,
	#	For each user that has 1 or more whistles that day
	#		get the count of the whistles
	#		get the time of the earliest whistle, and the latest whistle
	authed_whistles_per_user = (
		Whistle.objects
		.filter(
			is_authenticated=True, 
			datetime__date=requested_date)
		.exclude(request='PING')
		.values('user_id', 'datetime__date')
		.annotate(
			num_whistles=Count('user_id'), 
			min_time=Min('datetime'), 
			max_time=Max('datetime'),
			**status_code_annotations)
		.order_by('-max_time') )
	
	# Reformat the data for template rendering
	d = []
	for item in authed_whistles_per_user:
		status_counts = {str(code): item.get(f'count_{code}', 0) for code in status_codes}
		d.append({
			'user_id': item['user_id'],
			'date': item['datetime__date'],
			'num_whistles': item['num_whistles'],
			'min_time': item['min_time'],
			'max_time': item['max_time'],
			'status_counts': status_counts
		})
	authed_whistles_per_user = d

	### Unauthed whistles pseudo code
	#
	# For the selected day,
	#	For each user that has 1 or more whistles that day, and where one of the whistles is a PING
	#		get the count of the whistles
	#		get the time of the earliest whistle, and the latest whistle
	unauthed_whistles_per_user = (
		Whistle.objects
		.filter(
			is_authenticated=False, 
			datetime__date=requested_date)
		.exclude(request='PING')
		.values('user_id', 'datetime__date')
		.annotate(
			num_whistles=Count('user_id'), 
			min_time=Min('datetime'), 
			max_time=Max('datetime'),
			nonbot=Exists(view_helpers.nonbot_whistles_query),
			**status_code_annotations)
		.filter(nonbot=True)
		.order_by('-num_whistles') )
	
	# Reformat the data for template rendering
	d = []
	for item in unauthed_whistles_per_user:
		status_counts = {str(code): item.get(f'count_{code}', 0) for code in status_codes}
		d.append({
			'user_id': item['user_id'],
			'date': item['datetime__date'],
			'num_whistles': item['num_whistles'],
			'min_time': item['min_time'],
			'max_time': item['max_time'],
			'status_counts': status_counts
		})
	unauthed_whistles_per_user = d

	# Top platform (browser, device, etc), and viewport dimensions
	# These are per user in the given month. So if a user always has the same useragent, that will count as one. If they have 2 user agents in the month, that counts as 2. This is achieved by grouping the worthy whistles by useragent/viewport, and then counting the number of users who had that useragent/viewport.
	# Programming note: values() groups the queryset by the value, and an annotate count can be on any field (not just values() ones)

	worthy_useragents = (
		Whistle.objects
		.exclude(useragent='')
		.filter(is_authenticated=True, datetime__year=requested_date.year, datetime__month=requested_date.month)
		.values('datetime__date', 'user_id', 'useragent')
		.distinct()
		.annotate(user_and_date=Concat(F('datetime__date'), F('user_id'), output_field=CharField())) )
	top_useragents = (
		worthy_useragents
		.values('useragent')
		.annotate(sessions=Count('user_and_date', distinct=True))
		.order_by('-sessions')[:5] )
	total_useragents = worthy_useragents.values('user_and_date').count()
	
	worthy_viewports = (
		Whistle.objects
		.exclude(viewport_dimensions='')
		.filter(is_authenticated=True, datetime__year=requested_date.year, datetime__month=requested_date.month)
		.values('datetime__date', 'user_id', 'viewport_dimensions')
		.distinct()
		.annotate(user_and_date=Concat(F('datetime__date') ,F('user_id'), output_field=CharField())) 	)
	top_viewport_dimensions = (
		worthy_viewports
		.values('viewport_dimensions')
		.annotate(sessions=Count('user_and_date', distinct=True))
		.order_by('-sessions')[:5] )
	total_viewport_dimensions = worthy_viewports.values('user_and_date').count()

	# Get active django-invitations (https://github.com/jazzband/django-invitations) if that package is in the project
	if Invitation:
		invitations = Invitation.objects.filter(accepted=False)
	else:
		invitations = None

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
		'next_month': view_helpers.adjust_month(requested_date, 'next'),
		'previous_month': view_helpers.adjust_month(requested_date, 'previous'),
		'next_day': view_helpers.adjust_day(requested_date, 'next'),
		'previous_day': view_helpers.adjust_day(requested_date, 'previous'),
		'top_useragents': top_useragents,
		'total_useragents': total_useragents,
		'top_viewport_dimensions': top_viewport_dimensions,
		'total_viewport_dimensions': total_viewport_dimensions,
		'users': view_helpers.users_for_month(requested_date.year, requested_date.month),
		'invitations': invitations,
		'autolog_response_code': getattr(settings, 'WHISTLE_AUTOLOG_RESPONSE_CODE', True),
	})


@require_http_methods(["GET"])
@staff_member_required
def session(request, user_id, requested_date):
	'''Displays a table of all the whistles for the given user and date'''
	requested_date_with_tz = timezone.make_aware(datetime.fromisoformat(requested_date))
	requested_date = date.fromisoformat(requested_date)
	whistles = Whistle.objects.filter(datetime__date=requested_date_with_tz, user_id=user_id).exclude(request='PING').order_by('datetime')
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
		'autolog_request_method': getattr(settings, 'WHISTLE_AUTOLOG_REQUEST_METHOD', True),
		'autolog_request_path': getattr(settings, 'WHISTLE_AUTOLOG_REQUEST_PATH', True),
		'autolog_response_code': getattr(settings, 'WHISTLE_AUTOLOG_RESPONSE_CODE', True),
	})
	# TODO change the autolog context variables and template stuff to be about whether each part should be displayed, which is about whether at least one of a autolog type exists


@require_http_methods(["GET"])
@staff_member_required
def user_sessions(request, user_id=None):
	'''Lists all sessions for the given user - with dates and whistle counts.'''

	# Get the list of unique status codes for 4xx and 5xx responses.
	status_codes = Whistle.objects.filter(
		user_id=user_id,
		response_code__gte=400
	).exclude(request='PING').values_list('response_code', flat=True).distinct()

	# Build annotations for each status code.
	status_code_annotations = {
		f'count_{code}': Count(
			Case(
				When(response_code=code, then=1),
				output_field=IntegerField()
			)
		)
		for code in status_codes
	}

	# Get all whistles for given user and group into sessions
	sessions = (
		Whistle.objects
			.filter(user_id=user_id)
			.exclude(request='PING')
			.values('user_id', 'datetime__date', 'is_authenticated')
			.annotate(
				num_whistles=Count('user_id'), 
				min_time=Min('datetime'), 
				max_time=Max('datetime'),
				**status_code_annotations)
			.order_by('-min_time') )
	
	chart_labels, chart_data_values = view_helpers.get_user_sessions_chart_data(sessions)
	is_authenticated = sessions.first()['is_authenticated']

	# Reformat the data for template rendering
	d = []
	for item in sessions:
		status_counts = {str(code): item.get(f'count_{code}', 0) for code in status_codes}
		d.append({
			'user_id': item['user_id'],
			'date': item['datetime__date'],
			'num_whistles': item['num_whistles'],
			'min_time': item['min_time'],
			'max_time': item['max_time'],
			'status_counts': status_counts
		})
	sessions = d

	return TemplateResponse(request, 'silent_mammoth_whistle/user_sessions.html', {
		'user_id': user_id,
		'sessions': sessions,
		'chart_labels': chart_labels, 
		'chart_data_values': chart_data_values,
		'is_authenticated': is_authenticated,
		'autolog_response_code': getattr(settings, 'WHISTLE_AUTOLOG_RESPONSE_CODE', True),
	})