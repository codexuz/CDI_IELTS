# apps/profiles/apps.py
from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.profiles"

    def ready(self):
        # ensure signals are registered
        from . import signals  # noqa
