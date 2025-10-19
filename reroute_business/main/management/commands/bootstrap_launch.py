# main/management/commands/bootstrap_launch.py
# ------------------------------------------------------------
# One-time bootstrap: ensures Employer group + sample users.
# Usage: python manage.py bootstrap_launch
# ------------------------------------------------------------
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
from reroute_business.profiles.models import EmployerProfile, UserProfile

class Command(BaseCommand):
    help = "Bootstrap groups and test users for launch."

    @transaction.atomic
    def handle(self, *args, **opts):
        employer_group, _ = Group.objects.get_or_create(name="Employer")

        # --- Employer test user ---
        emp, created = User.objects.get_or_create(
            username="testemployer",
            defaults={"email": "employer@example.com", "first_name": "Test", "last_name": "Employer"}
        )
        if created:
            emp.set_password("TestPass123!")
            emp.save()
            self.stdout.write(self.style.SUCCESS("Created employer user."))

        emp.groups.add(employer_group)
        EmployerProfile.objects.get_or_create(user=emp, defaults={"company_name": "Test Co"})

        # --- Seeker test user ---
        seeker, created = User.objects.get_or_create(
            username="testseeker",
            defaults={"email": "seeker@example.com", "first_name": "Test", "last_name": "Seeker"}
        )
        if created:
            seeker.set_password("TestPass123!")
            seeker.save()
            self.stdout.write(self.style.SUCCESS("Created seeker user."))

        UserProfile.objects.get_or_create(user=seeker)

        self.stdout.write(self.style.SUCCESS("Bootstrap complete."))
