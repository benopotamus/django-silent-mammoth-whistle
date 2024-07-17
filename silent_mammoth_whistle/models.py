from django.db import models

class Whistle(models.Model):
	user_id = models.TextField()
	request = models.TextField(blank=True)
	response = models.TextField(blank=True)
	datetime = models.DateTimeField(auto_now_add=True)
	useragent = models.TextField(blank=True)
	viewport_dimensions = models.TextField(blank=True)

	is_client_event = models.BooleanField(default=False)
	is_authenticated = models.BooleanField(default=False)

	# We'll leave indexes out until we need them.
	# class Meta:
	# 	indexes = [
	# 		models.Index(fields=["user_id", "useragent"]),
	# 	]
