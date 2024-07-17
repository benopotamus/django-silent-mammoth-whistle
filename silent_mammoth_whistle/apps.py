from django.apps import AppConfig


class SilentMammothWhistleConfig(AppConfig):
	name = "silent_mammoth_whistle"
	verbose_name = "Silent mammoth whistle"

	def ready(self):
		# Implicitly connect signal handlers decorated with @receiver.
		from . import signals