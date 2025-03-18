from django.conf import settings
from django.http import HttpResponse
from .forms import WhistleForm

# Set up variables from settings file
user_id_field = getattr(settings, 'WHISTLE_USER_ID_FIELD', 'id')
client_event_path = getattr(settings, 'WHISTLE_CLIENT_EVENT_PATH', '/whistle')
use_cookies = getattr(settings, 'WHISTLE_COOKIES', True)
autolog_request_method = getattr(settings, 'WHISTLE_AUTOLOG_REQUEST_METHOD', True)
autolog_request_path = getattr(settings, 'WHISTLE_AUTOLOG_REQUEST_PATH', True)
autolog_response_code = getattr(settings, 'WHISTLE_AUTOLOG_RESPONSE_CODE', True)


class Whistle:
	def __init__(self):
		self._request = []
		self._response = []

	def request(self, *args):
		self._request.extend(str(arg) for arg in args)

	def response(self, *args):
		self._response.extend(str(arg) for arg in args)


class HttpResponseNoContent(HttpResponse):
    status_code = 204 # No content


def save_whistle(request, response, is_client_event=False):
	# Save whistle to database, but not for admins
	if not request.user.is_staff:
		# We only save whistles if an AUTOLOG setting is on or the user has explicitly added stuff to the whistle
		if autolog_request_method or autolog_request_path or autolog_response_code or len(request.whistle._request) or len(request.whistle._response):

			if request.user.is_authenticated:
				try:
					user_id = getattr(request.user, user_id_field)
				except AttributeError:
					# If the user object doesn't have an attribute with the name specified in user_id_field, just use user.id instead
					user_id = request.user.id
			else:
				# If user isn't logged in, we use their session_key as the user_id instead
				# Without this, all requests from anonymous users would be grouped into a single session
				if not request.session.session_key:
					request.session.save() # A session needs to be saved at least once to generate a session key. We don't want to save every time though, just if there's no key yet
					request.session['anonymous_session_key'] = request.session.session_key # We make a copy of the key in the session object because the key changes when the user authenticates and we want to update whistle records that have the anonymous session key to use the user id when the user logs in - see signals.py
				user_id = request.session.session_key

			# Note: The values for AUTOLOG settings are always saved, the AUTOLOG settings just say whether they should be included in the rendered output automatically.
			data={
				'user_id': str(user_id), 
				'request': "\t".join(request.whistle._request),
				'request_method': 'CLIENT' if is_client_event else request.method,
				'request_path': '' if is_client_event else request.path,
				'response': "\t".join(request.whistle._response),
				'response_code': response.status_code,
				'is_authenticated': request.user.is_authenticated,
				'viewport_dimensions': request.COOKIES.get('viewport_dimensions', ''),

				# Save these meta values if present, or save an empty string if not
				'referer': str( dict.get(request.META, 'HTTP_REFERER', '') ),
				'useragent': str( dict.get(request.META, 'HTTP_USER_AGENT', '') ), 
			}

			form = WhistleForm(data=data)
			if form.is_valid():
				form.save()
			else:
				# Error
				print('Whistle error 🪈⚠️')
				print(form.errors)


class SilentMammothWhistleMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):

		# Don't do anything for HEAD requests
		if request.method == "HEAD":
			return self.get_response(request)

		### 1. Request part of lifecycle
		request.whistle = Whistle()

		# If the whistle is from the client, log it as an event, and prevent request from reaching views.py by returning a response early
		if request.path == client_event_path:
			request.whistle.request(request.POST.get('args', '')) # Add the 'args' data from the POST request to the whistle object
			response = HttpResponseNoContent() # Prevent views.py from processing request (by not creating a new response with get_response)
			save_whistle(request, response, is_client_event=True) # Save whistle
			return response

		### 2. Calling View part of lifecycle
		response = self.get_response(request)

		if use_cookies and 'viewport_dimensions' not in request.COOKIES:
			response.set_cookie('viewport_dimensions', samesite='Strict') # Defaults to path=/

		### 3. Response part of lifecycle
		save_whistle(request, response)

		return response
	