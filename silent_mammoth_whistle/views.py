from datetime import date

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.dateformat import format as format_date
from django.views.decorators.http import require_http_methods

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
	'''The homepage of silent_mammoth_whistle. It displays the day's sessions, and a graph of the month's unique sessions.

	requested_date should be of the form '2019-12-04'
	'''
	# Get active django-invitations (https://github.com/jazzband/django-invitations) if that package is in the project
	invitations = Invitation.objects.filter(accepted=False) if Invitation else None

	if requested_date is None:
		requested_date = date.today()
	else:
		requested_date = date.fromisoformat(requested_date)

	chart = view_helpers.monthly_chart_data(requested_date)
	top_useragents, total_useragents = view_helpers.top_field_counts(requested_date, 'useragent')
	top_viewport_dimensions, total_viewport_dimensions = view_helpers.top_field_counts(requested_date, 'viewport_dimensions')

	return TemplateResponse(request, 'silent_mammoth_whistle/index.html', {
		'date': requested_date,
		'day_str': format_date(requested_date, "l jS"),
		'day': requested_date.day - 1,  # Index of the selected day's bar in the chart
		'chart_period': requested_date.strftime("%B %Y"),
		'chart_dates': chart['dates'],
		'chart_xaxis_labels': chart['xaxis_labels'],
		'authed_chart_data': chart['authed_data'],
		'unauthed_chart_data': chart['unauthed_data'],
		'chart_error_flags': chart['error_flags'],
		'month_has_whistles': any(chart['authed_data'] + chart['unauthed_data']),
		'authed_whistles_per_user': view_helpers.sessions_for_day(requested_date, is_authenticated=True),
		'unauthed_whistles_per_user': view_helpers.sessions_for_day(requested_date, is_authenticated=False),
		'next_month': view_helpers.adjust_month(requested_date, 'next'),
		'previous_month': view_helpers.adjust_month(requested_date, 'previous'),
		'next_day': view_helpers.adjust_day(requested_date, 'next'),
		'previous_day': view_helpers.adjust_day(requested_date, 'previous'),
		'top_useragents': top_useragents,
		'total_useragents': total_useragents,
		'top_viewport_dimensions': top_viewport_dimensions,
		'total_viewport_dimensions': total_viewport_dimensions,
		'users': view_helpers.users_for_month(requested_date),
		'invitations': invitations,
		'show_response_code': getattr(settings, 'WHISTLE_AUTOLOG_RESPONSE_CODE', True),
	})


@require_http_methods(["GET"])
@staff_member_required
def session(request, user_id, requested_date):
	'''Displays a table of all the whistles for the given user and date'''
	requested_date = date.fromisoformat(requested_date)
	start, end = view_helpers.day_bounds(requested_date)

	whistles = list(
		Whistle.objects
		.filter(user_id=user_id, datetime__gte=start, datetime__lt=end)
		.exclude(request='PING')
		.order_by('datetime'))

	if not whistles:
		raise Http404('No whistles for this user and date')

	return TemplateResponse(request, 'silent_mammoth_whistle/session.html', {
		'user_id': user_id,
		'date': requested_date,
		'date_str': requested_date.strftime("%A %d %B %Y"),
		'whistles': whistles,
		'min_time': whistles[0].datetime,
		'max_time': whistles[-1].datetime,
		'useragent': whistles[0].useragent,
		'viewport_dimensions': next((w.viewport_dimensions for w in whistles if w.viewport_dimensions), ''),
		'is_authenticated': whistles[0].is_authenticated,
		'show_request_method': getattr(settings, 'WHISTLE_AUTOLOG_REQUEST_METHOD', True),
		'show_request_path': getattr(settings, 'WHISTLE_AUTOLOG_REQUEST_PATH', True),
		'show_response_code': getattr(settings, 'WHISTLE_AUTOLOG_RESPONSE_CODE', True),
	})


@require_http_methods(["GET"])
@staff_member_required
def user_sessions(request, user_id=None):
	'''Lists all sessions for the given user - with dates and whistle counts.'''
	sessions = view_helpers.sessions_for_user(user_id)

	if not sessions:
		raise Http404('No whistles for this user')

	chart_labels, chart_data_values = view_helpers.user_sessions_chart_data(sessions)

	return TemplateResponse(request, 'silent_mammoth_whistle/user_sessions.html', {
		'user_id': user_id,
		'sessions': sessions,
		'chart_labels': chart_labels,
		'chart_data_values': chart_data_values,
		'is_authenticated': sessions[0]['is_authenticated'],
		'show_response_code': getattr(settings, 'WHISTLE_AUTOLOG_RESPONSE_CODE', True),
	})
