from django.apps import AppConfig

class ProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reroute_business.profiles'

    def ready(self):
        import reroute_business.profiles.signals
