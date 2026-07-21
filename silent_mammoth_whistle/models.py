from django.db import models
from django.db.models import Q

class Whistle(models.Model):
	HTTP_METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
        ('OPTIONS', 'OPTIONS'),
        ('HEAD', 'HEAD'),
        ('CLIENT', 'CLIENT'),
    ]

	# user_id holds either the id of an authenticated user (see settings.WHISTLE_USER_ID_FIELD)
	# or the session key of an anonymous user. It stays a TextField (rather than a sized
	# CharField) so existing data can never be truncated; SQLite and PostgreSQL index text
	# columns without needing a length.
	user_id = models.TextField()

	request = models.TextField(blank=True)
	request_method = models.CharField(
        max_length=10,
        choices=HTTP_METHOD_CHOICES,
        default=''
    )
	request_path = models.TextField(blank=True, default='')

	response = models.TextField(blank=True)
	response_code = models.IntegerField(default=0)

	referer = models.TextField(blank=True)

	datetime = models.DateTimeField(auto_now_add=True)
	useragent = models.TextField(blank=True)
	viewport_dimensions = models.TextField(blank=True)

	is_authenticated = models.BooleanField(default=False)

	class Meta:
		indexes = [
			# For day/month range filters used by every page.
			models.Index(fields=['datetime'], name='smw_datetime_idx'),

			# For bot-check subquery (user_id + request='PING'), the user_sessions page, and the login signal's UPDATE.
			models.Index(fields=['user_id'], name='smw_user_id_idx'),

			# For index page.
			models.Index(fields=['is_authenticated', 'datetime'], name='smw_auth_datetime_idx'),

			# Partial index covering only 'PING' whistles, which the bot filter (view_helpers.nonbot_user_ids) selects on. 
			# It stays small because it only contains PING rows. Supported by SQLite and PostgreSQL.
			models.Index(fields=['user_id'], condition=Q(request='PING'), name='smw_ping_user_idx'),
		]
