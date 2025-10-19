from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
# from employers.models import EmployerProfile  # Leave this commented until you're ready
from reroute_business.profiles.models import UserProfile

class Command(BaseCommand):
    help = 'Create test users for dashboards'

    def handle(self, *args, **kwargs):
        # ✅ Regular User
        user, created = User.objects.get_or_create(username='test_user')
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(self.style.SUCCESS("✅ test_user created."))
        else:
            self.stdout.write("⚠️ test_user already exists.")

        UserProfile.objects.get_or_create(user=user)

        # 🏢 Employer
        employer, created = User.objects.get_or_create(username='test_employer')
        if created:
            employer.set_password('testpass123')
            employer.save()
            self.stdout.write(self.style.SUCCESS("🏢 test_employer created."))
        else:
            self.stdout.write("⚠️ test_employer already exists.")

        # Uncomment when EmployerProfile is ready
        # EmployerProfile.objects.get_or_create(user=employer, defaults={'company_name': 'Test Corp'})

        # 🛠️ Superuser
        if not User.objects.filter(username='test_admin').exists():
            User.objects.create_superuser(username='test_admin', email='', password='testpass123')
            self.stdout.write(self.style.SUCCESS("🛠️ test_admin created."))
        else:
            self.stdout.write("⚠️ test_admin already exists.")
