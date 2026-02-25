from django.apps import AppConfig


class ReentryOrgConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reroute_business.reentry_org"
    label = "reentry_org"
    verbose_name = "Reentry Orgs"

    def ready(self):
        import reroute_business.reentry_org.signals  # noqa: F401
