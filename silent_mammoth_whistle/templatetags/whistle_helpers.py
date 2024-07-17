import re, user_agents
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.conf import settings

register = template.Library()

@register.simple_tag
def time_duration(min, max, short_units=False):
	"""Returns a nice string of a time delta"""
	delta = max - min

	seconds = delta.total_seconds() % (24 * 3600)
	hours = seconds // 3600
	seconds %= 3600
	minutes = seconds // 60
	seconds %= 60

	if short_units:
		units = ['h', 'm', 's']
	else:
		units = [' hrs', ' mins', ' secs']

	result = []
	if hours > 0:
		result.append(f'{int(hours)}{units[0]}')
	if minutes > 0:
		result.append(f'{int(minutes)}{units[1]}')
	if seconds > 0:
		result.append(f'{int(seconds)}{units[2]}')
	
	if result:
		return ", ".join(result)
	else:
		# If there is only a single whistle in the session, then there will be no time duration (min and max are the same). Default to "0 secs" if that happens.
		return f'0 {units[2]}'

	# return datetime.datetime.strptime(str(delta),'%H:%M:%S').time()

@register.simple_tag
def time_duration_condensed(min, max):
	return time_duration(min, max, short_units=True)

@register.simple_tag
def percentage(num, total):
	return f'{round(num/total*100)}%'

@register.filter
def browser_change(whistle, previous_whistle):
	"""
	Returns true if the browser changed between whistles.
	Ignores empty strings, which can occur because the viewport_dimensions cookie wasn't populated yet (on first request) or the header is missing for some reason (I don't know why it is omitted sometimes)
	"""
	return (
		whistle.useragent != '' 
		and previous_whistle.useragent != '' 
		and whistle.useragent != previous_whistle.useragent
	) or (
		whistle.viewport_dimensions != '' 
		and previous_whistle.viewport_dimensions != '' 
		and whistle.viewport_dimensions != previous_whistle.viewport_dimensions)

@register.filter(is_safe=True)
def html_tabs(value):
	'''Converts tab character to html tabs (4 x nbsp)'''
	return mark_safe(escape(value).replace("\t","&nbsp;&nbsp;&nbsp;&nbsp;"))

@register.filter(is_safe=True)
def small_guids(str):
	'''Replace guids with some html that contains an abbrieviated guid and a long version in a tooltip'''
	# Regular expression to match a GUID
	guid_pattern = re.compile(r'\b[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}\b')
	def replace_guid(match):
		guid = match.group(0)
		shortened_guid = f"<abbr title='{guid}'>{guid[:3]}...{guid[-3:]}</abbr>"
		return shortened_guid
	# Substitute all GUIDs in the string with their shortened versions
	return re.sub(guid_pattern, replace_guid, str)

@register.filter
def preferred_user_id(user):
	user_id_field = getattr(settings, 'WHISTLE_USER_ID_FIELD', 'id')
	try:
		return getattr(user, user_id_field)
	except AttributeError:
		# If the user object doesn't have an attribute with the name specified in user_id_field, just use user.id instead
		return user.id

@register.filter
def forloop_next(some_list, current_index):
	"""
	Returns the next element of the list using the current index if it exists.
	Otherwise returns an empty string.
	"""
	try:
		return some_list[int(current_index) + 1] # access the next element
	except:
		return '' # return empty string in case of exception

@register.filter
def forloop_previous(some_list, current_index):
	"""
	Returns the previous element of the list using the current index if it exists.
	Otherwise returns an empty string.
	"""
	try:
		return some_list[int(current_index) - 1] # access the previous element
	except:
		return '' # return empty string in case of exception

@register.filter(is_safe=True)
def ua_parse(ua_string):
	"""
	Returns a useful string from user agent data.a pretty html representation of a user agent. 
	E.g. "iPhone / iOS 5.1 / Mobile Safari 5.1"
	"""
	user_agent = user_agents.parse(ua_string)
	return mark_safe(escape(str(user_agent))) # returns 

@register.filter
def ua_is_bot(ua_string):
	"""
	Bot filtering. Returns true if user agent string looks like a bot

	From shynet/analytics/tasks.py
	"""
	ua = user_agents.parse(ua_string)
	return (
		ua.is_bot
		or (ua.browser.family or "").strip().lower() == "googlebot"
		or (ua.device.family or ua.device.model or "").strip().lower() == "spider"
	)
