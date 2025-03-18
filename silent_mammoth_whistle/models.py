from django.db import models

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

	# We'll leave indexes out until we need them.
	# class Meta:
	# 	indexes = [
	# 		models.Index(fields=["user_id", "useragent"]),
	# 	]
