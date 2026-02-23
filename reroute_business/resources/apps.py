from django.apps import AppConfig


class ResourcesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reroute_business.resources'

    def ready(self):
        import reroute_business.resources.signals  # noqa: F401
