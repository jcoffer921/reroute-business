from django.apps import AppConfig


class ResumesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'resumes'

    def ready(self):
        # Import signals to attach receivers
        try:
            import resumes.signals  # noqa: F401
        except Exception:
            # Avoid hard failure during initial migrations
            pass
