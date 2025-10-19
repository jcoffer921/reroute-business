from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.timezone import make_aware

from reroute_business.job_list.models import Job, Application
from reroute_business.dashboard.models import Interview


class Command(BaseCommand):
    help = "Seed a couple of sample interviews for quick testing"

    def handle(self, *args, **options):
        # Ensure employer and candidate exist
        employer, _ = User.objects.get_or_create(username='test_employer', defaults={'email': ''})
        if not employer.has_usable_password():
            employer.set_password('testpass123')
            employer.save()

        candidate, _ = User.objects.get_or_create(username='test_user', defaults={'email': ''})
        if not candidate.has_usable_password():
            candidate.set_password('testpass123')
            candidate.save()

        # Ensure the employer has at least one job
        job = Job.objects.filter(employer=employer).order_by('-created_at').first()
        if not job:
            job = Job.objects.create(
                title='Warehouse Associate',
                description='Assist with inbound/outbound shipments and inventory.',
                requirements='Ability to lift 50 lbs, basic computer skills',
                location='Philadelphia, PA',
                zip_code='19104',
                employer=employer,
                tags='warehouse,shipping',
                job_type='full_time',
                salary_type='hour',
                hourly_min=18.50,
                hourly_max=24.00,
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Created sample job: {job.title}"))

        # Ensure the candidate has applied to employer jobs (privacy scope for autocomplete)
        app, created = Application.objects.get_or_create(applicant=candidate, job=job)
        if created:
            self.stdout.write(self.style.SUCCESS("✅ Created sample application"))

        # Create two sample interviews (future)
        when1 = make_aware(datetime.now() + timedelta(days=2, hours=3))
        when2 = make_aware(datetime.now() + timedelta(days=5, hours=1))

        iv1, created1 = Interview.objects.get_or_create(
            job=job, employer=employer, candidate=candidate, scheduled_at=when1,
            defaults={'status': Interview.STATUS_PLANNED, 'notes': 'Phone screen'}
        )
        iv2, created2 = Interview.objects.get_or_create(
            job=job, employer=employer, candidate=candidate, scheduled_at=when2,
            defaults={'status': Interview.STATUS_PLANNED, 'notes': 'On-site'}
        )

        if created1 or created2:
            self.stdout.write(self.style.SUCCESS("✅ Seeded sample interviews"))
        else:
            self.stdout.write("ℹ️ Sample interviews already exist")
