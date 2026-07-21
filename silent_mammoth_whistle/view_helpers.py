import calendar
from collections import Counter
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import CharField, Count, F, Max, Min
from django.db.models.functions import Concat, TruncDate
from django.utils import timezone

from .models import Whistle

User = get_user_model()
USER_ID_FIELD = getattr(settings, 'WHISTLE_USER_ID_FIELD', 'id')


def day_bounds(day):
	"""Returns the start and end of a day, with end being the first moment of the next day."""
	start = datetime.combine(day, time.min)
	if settings.USE_TZ:
		start = timezone.make_aware(start)
	return start, start + timedelta(days=1)


def month_bounds(day):
	"""Returns the start and end of the month that the day is in, with end being the first day of the next month."""
	first = day.replace(day=1)
	if first.month == 12:
		next_first = date(first.year + 1, 1, 1)
	else:
		next_first = date(first.year, first.month + 1, 1)
	return day_bounds(first)[0], day_bounds(next_first)[0]


def month_dates(day):
	"""Returns a list of date objects, one for every day of the month that `day` falls in."""
	num_days = calendar.monthrange(day.year, day.month)[1]
	return [date(day.year, day.month, n) for n in range(1, num_days + 1)]


def current_day():
	"""Returns today's date in the same timezone the whistle queries group by."""
	return timezone.localdate() if settings.USE_TZ else date.today()


# ---------------------------------------------------------------------------
# Caching
#
# Whistles from days before today can never change: the middleware only creates
# whistles "now", and signals.on_login only rewrites/deletes whistles from the
# current day. So any aggregate computed over a range that ends before the start
# of today is immutable and safe to cache indefinitely.
#
# Each month-scoped helper below splits its range at the start of today: the
# immutable part [month start, today) is cached, today's slice is computed live,
# and the two are merged. Because every aggregate on the index page decomposes
# per day (sessions are (user, day) pairs), the merge is exact.
#
# Caching is off unless settings.WHISTLE_CACHE = True. Django's default
# in-process cache backend works fine; entries are small (a month of aggregates,
# not whistles). WHISTLE_CACHE_TIMEOUT (seconds, default 30 days) exists mainly
# as hygiene so retired keys eventually vanish from persistent cache backends.
# ---------------------------------------------------------------------------

def _cached(key, compute):
	"""Returns compute(), cached under `key` when WHISTLE_CACHE is enabled. Only use for results that can no longer change."""
	if not getattr(settings, 'WHISTLE_CACHE', False):
		return compute()
	value = cache.get(key)
	if value is None:
		value = compute()
		cache.set(key, value, getattr(settings, 'WHISTLE_CACHE_TIMEOUT', 60 * 60 * 24 * 30))
	return value


def _immutable_split(start, end):
	"""Returns the datetime within [start, end] that separates the immutable past ([start, split)) from the still-changing present ([split, end))."""
	return min(max(day_bounds(current_day())[0], start), end)


def adjust_month(date, direction):
	"""Returns a date string (yyyy-mm-01) that is the 1st of the next or previous month.

	Direction can be "next", which increases the month by 1, or "previous", which reduces the month by 1
	"""
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
	return f"{new_year:04d}-{new_month:02d}-01"


def adjust_day(date, direction):
	"""Returns a date string (yyyy-mm-dd) that is one day forward or backwards in time.

	Direction can be "next", which increases the day by 1, or "previous", which reduces the day by 1
	"""
	if direction == "next":
		adjusted_date = date + timedelta(days=1)
	elif direction == "previous":
		adjusted_date = date - timedelta(days=1)
	else:
		raise ValueError("The direction parameter must be 'next' or 'previous'")
	return adjusted_date.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Session queries
# ---------------------------------------------------------------------------

# This subquery returns the set of user_ids that belong to real browsers rather than bots. It's used when creating data for charts (monthly_chart_data) and for sessions themselves.
# A user counts as a real browser if any of their whistles is a 'PING'. Most malicious bots don't seem to execute the JavaScript that sends the 'PING' request.
# Some good bots (like Google Bot and BingBot) do execute the 'PING' request so we just filter for 'bot' useragents as well.
# It's used as `user_id__in=nonbot_user_ids`
nonbot_user_ids = (
	Whistle.objects
	.filter(request='PING')
	.exclude(useragent__icontains='bot')
	.exclude(useragent__contains='HeadlessChrome')
	.values('user_id')
)


def _error_counts(whistles):
	"""Returns {(user_id, date): {'404': 2, '500': 1, ...}} counting 4xx/5xx responses in the given whistle queryset."""
	rows = (
		whistles
		.filter(response_code__gte=400)
		.values('user_id', 'datetime__date', 'response_code')
		.annotate(count=Count('id'))
		.order_by('response_code'))

	counts = {}
	for row in rows:
		key = (row['user_id'], row['datetime__date'])
		counts.setdefault(key, {})[str(row['response_code'])] = row['count']
	return counts


def _format_session_rows(sessions, error_counts):
	"""Formats grouped session rows (and their error counts) into the plain dicts the templates render."""
	return [{
		'user_id': row['user_id'],
		'date': row['datetime__date'],
		'is_authenticated': row.get('is_authenticated'),
		'num_whistles': row['num_whistles'],
		'min_time': row['min_time'],
		'max_time': row['max_time'],
		'status_counts': error_counts.get((row['user_id'], row['datetime__date']), {}),
	} for row in sessions]


def sessions_for_day(day, is_authenticated):
	"""Returns one row (dict) per user who whistled on `day`: whistle count, first/last whistle times, and per-status-code error counts.

	Authenticated sessions are ordered by most recent activity; unauthenticated ones are filtered to sessions that look like real browsers (see nonbot_user_ids) and ordered by whistle count.

	Days before today are immutable, so their tables are cached when WHISTLE_CACHE is True; today is always computed live.

	Uses datetime__gte and datetime__lt to support using database indexes.
	"""
	if day < current_day():
		return _cached(
			f'smw1:sessions:{day}:{1 if is_authenticated else 0}',
			lambda: _sessions_for_day(day, is_authenticated))
	return _sessions_for_day(day, is_authenticated)


def _sessions_for_day(day, is_authenticated):
	start, end = day_bounds(day)
	whistles = (
		Whistle.objects
		.filter(is_authenticated=is_authenticated, datetime__gte=start, datetime__lt=end)
		.exclude(request='PING'))

	sessions = (
		whistles
		.values('user_id', 'datetime__date')
		.annotate(
			num_whistles=Count('id'),
			min_time=Min('datetime'),
			max_time=Max('datetime')))

	if is_authenticated:
		sessions = sessions.order_by('-max_time')
	else:
		sessions = (
			sessions
			.filter(user_id__in=nonbot_user_ids)
			.order_by('-num_whistles'))

	return _format_session_rows(sessions, _error_counts(whistles))


def sessions_for_user(user_id):
	"""Returns one row (dict) per session (i.e. per day of activity) for the given user, most recent first."""
	whistles = Whistle.objects.filter(user_id=user_id).exclude(request='PING')

	sessions = (
		whistles
		.values('user_id', 'datetime__date', 'is_authenticated')
		.annotate(
			num_whistles=Count('id'),
			min_time=Min('datetime'),
			max_time=Max('datetime'))
		.order_by('-min_time'))

	return _format_session_rows(sessions, _error_counts(whistles))


# ---------------------------------------------------------------------------
# Monthly stats
# ---------------------------------------------------------------------------

def monthly_chart_data(day):
	"""Returns the data for the "Sessions per day" chart on the index page, for the month `day` falls in:

	{
		'dates': ['2026-07-01', ...],        one entry per day of the month
		'xaxis_labels': [1, 2, ...],         day numbers
		'authed_data': [3, 0, ...],          unique non-bot users per day
		'unauthed_data': [5, 1, ...],
		'error_flags': [0, 1, ...],          1 if the day had any 4xx/5xx response
	}

	The whole chart - bars and error stripes - describes non-bot traffic only.
	The part of the month before today is immutable and cached when WHISTLE_CACHE is True; today's slice is always computed live and merged in.
	"""
	start, end = month_bounds(day)
	split = _immutable_split(start, end)

	authed, unauthed, error_dates = {}, {}, set()
	if split > start:
		past = _cached(f'smw1:chart:{start.date()}:{split.date()}', lambda: _chart_portion(start, split))
		authed.update(past[0]); unauthed.update(past[1]); error_dates |= past[2]
	if end > split:
		live = _chart_portion(split, end)
		authed.update(live[0]); unauthed.update(live[1]); error_dates |= live[2]

	dates = month_dates(day)
	return {
		'dates': [str(d) for d in dates],
		'xaxis_labels': [d.day for d in dates],
		'authed_data': [authed.get(d, 0) for d in dates],
		'unauthed_data': [unauthed.get(d, 0) for d in dates],
		'error_flags': [1 if d in error_dates else 0 for d in dates],
	}


def _chart_portion(start, end):
	"""Returns (authed {date: users}, unauthed {date: users}, error_dates set) for non-bot whistles in [start, end).
	Uses datetime__gte and datetime__lt to support using database indexes.
	"""
	whistles = (
		Whistle.objects
		.filter(datetime__gte=start, datetime__lt=end)
		.filter(user_id__in=nonbot_user_ids)
		.exclude(request='PING'))

	rows = (
		whistles
		.values('datetime__date', 'is_authenticated')
		.annotate(num_sessions=Count('user_id', distinct=True)))

	authed, unauthed = {}, {}
	for row in rows:
		target = authed if row['is_authenticated'] else unauthed
		target[row['datetime__date']] = row['num_sessions']

	error_dates = set(
		whistles
		.filter(response_code__gte=400)
		.values_list('datetime__date', flat=True)
		.distinct())

	return authed, unauthed, error_dates


def top_field_counts(day, field):
	"""Returns (top, total) for the given field ('useragent' or 'viewport_dimensions') among authenticated whistles in the month `day` falls in.

	`top` is the 5 most common values with their session counts; `total` is the denominator for percentages. Counting is per user-session (user + day): a user with the same useragent all month counts once per active day, and a user with 2 useragents in a session counts once for each.
	"""
	start, end = month_bounds(day)
	split = _immutable_split(start, end)

	counts = Counter()
	if split > start:
		counts.update(_cached(f'smw1:top:{field}:{start.date()}:{split.date()}', lambda: _field_session_counts(start, split, field)))
	if end > split:
		counts.update(_field_session_counts(split, end, field))

	top = [{field: value, 'sessions': sessions} for value, sessions in counts.most_common(5)]
	# The distinct session counts partition the (day, user, field) triples, so their sum is the total number of triples.
	return top, sum(counts.values())


def _field_session_counts(start, end, field):
	"""Returns {field value: distinct (day, user) session count} for authenticated whistles in [start, end).
	Uses datetime__gte and datetime__lt to support using database indexes.
	"""
	worthy = (
		Whistle.objects
		.exclude(**{field: ''})
		.filter(is_authenticated=True, datetime__gte=start, datetime__lt=end)
		.values('datetime__date', 'user_id', field)
		.distinct()
		.annotate(user_and_date=Concat(F('datetime__date'), F('user_id'), output_field=CharField())))

	rows = (
		worthy
		.values(field)
		.annotate(sessions=Count('user_and_date', distinct=True))
		.order_by('-sessions'))

	return {row[field]: row['sessions'] for row in rows}


def users_for_month(day):
	"""Returns the authenticated users active in the month `day` falls in, with their session (active-day) counts, most active first. Users who joined during that month are flagged is_new.
	"""
	start, end = month_bounds(day)
	split = _immutable_split(start, end)

	counts = Counter()
	if split > start:
		counts.update(_cached(f'smw1:users:{start.date()}:{split.date()}', lambda: _user_session_counts(start, split)))
	if end > split:
		counts.update(_user_session_counts(split, end))

	new_user_ids = {
		str(value) for value in
		User.objects
			.filter(date_joined__year=day.year, date_joined__month=day.month)
			.values_list(USER_ID_FIELD, flat=True)
	}

	return [{
		'user_id': user_id,
		'sessions': sessions,
		'is_new': user_id in new_user_ids,
	} for user_id, sessions in counts.most_common()]


def _user_session_counts(start, end):
	"""Returns {user_id: number of active days} for authenticated whistles in [start, end).
	Uses datetime__gte and datetime__lt to support using database indexes.
	"""
	rows = (
		Whistle.objects
		.filter(is_authenticated=True, datetime__gte=start, datetime__lt=end)
		.exclude(request='PING')
		.annotate(whistle_date=TruncDate('datetime'))
		.values('user_id')
		.annotate(sessions=Count('whistle_date', distinct=True)))

	return {row['user_id']: row['sessions'] for row in rows}


def user_sessions_chart_data(session_rows):
	"""Returns (labels, values) for the per-user "whistles per day" chart: one entry per day between the user's first and last sessions, zero-filled for inactive days."""
	if not session_rows:
		return [], []

	per_day = {row['date']: row['num_whistles'] for row in session_rows}
	first, last = min(per_day), max(per_day)
	days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
	return [d.strftime('%Y-%m-%d') for d in days], [per_day.get(d, 0) for d in days]
