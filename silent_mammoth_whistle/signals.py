from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.conf import settings
from .models import Whistle

user_id_field = getattr(settings, 'WHISTLE_USER_ID_FIELD', 'id')


@receiver(user_logged_in)
def on_login(sender, user, request, **kwargs):
	'''Replace the session user id in all whistle records with the user's actual id (as defined by settings.WHISTLE_USER_ID_FIELD) when the user logs in. This is how we connect the whistles of an anonymous session to an eventual logged in one.'''
	
	if 'anonymous_session_key' in request.session:

		# If the (previously) anonymous user is_staff, delete the whistles for that session. We don't want to see staff usage.
		if request.user.is_staff:
			Whistle.objects.filter(user_id=request.session['anonymous_session_key']).delete()
		else:
			# If the user object doesn't have an attribute with the name specified in user_id_field, just use user.id instead
			user_id = getattr(request.user, user_id_field, request.user.id)
			# Update records with authenticated user id
			Whistle.objects.filter(user_id=request.session['anonymous_session_key']).update(user_id=user_id, is_authenticated=True)
