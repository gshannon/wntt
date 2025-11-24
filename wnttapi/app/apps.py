from django.apps import AppConfig
from django.core.cache import cache


class WnttApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        # Our cache backend is file-based, so clear it on startup to avoid stale data.
        cache.clear()
