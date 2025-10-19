from django.core.management.base import BaseCommand
from reroute_business.profiles.models import UserProfile
from datetime import datetime

class Command(BaseCommand):
    help = 'Backfill user_uid values'

    def handle(self, *args, **kwargs):
        updated = 0
        for profile in UserProfile.objects.filter(user_uid__isnull=True):
            if profile.user and profile.user.id:
                uid = f"RR-{profile.user.date_joined.year}-{profile.user.id:06d}"
            else:
                year = datetime.now().year
                count = UserProfile.objects.filter(user_uid__startswith=f"RR-{year}").count() + 1
                uid = f"RR-{year}-TEMP{count:06d}"
            profile.user_uid = uid
            profile.save()
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Backfilled {updated} profiles."))
