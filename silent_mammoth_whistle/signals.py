from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.conf import settings
from .models import Whistle
from .view_helpers import current_day, day_bounds

user_id_field = getattr(settings, 'WHISTLE_USER_ID_FIELD', 'id')


@receiver(user_logged_in)
def on_login(sender, user, request, **kwargs):
	"""Replace the session user id in the current day's whistle records with the user's actual id (as defined by settings.WHISTLE_USER_ID_FIELD) when the user logs in. This is how we connect the whistles of an anonymous session to an eventual logged in one.

	Only whistles from the current day are altered: a session is a (user, day) pair, so an anonymous visit on an earlier day stays as its own unauthenticated session. This also means whistles from days before today never change. The benefit of this limitation is speed improvements and caching.
	"""

	if 'anonymous_session_key' in request.session:
		session_whistles = Whistle.objects.filter(
			user_id=request.session['anonymous_session_key'],
			datetime__gte=day_bounds(current_day())[0])

		# If the (previously) anonymous user is_staff, delete the whistles for that session. We don't want to see staff usage.
		if request.user.is_staff:
			session_whistles.delete()
		else:
			# If the user object doesn't have an attribute with the name specified in user_id_field, just use user.id instead
			user_id = getattr(request.user, user_id_field, request.user.id)
			# Update records with authenticated user id
			session_whistles.update(user_id=user_id, is_authenticated=True)
