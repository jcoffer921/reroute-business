from django.core.management.base import BaseCommand

from reroute_business.resumes.models import Resume
from reroute_business.resumes.utils.preview import generate_resume_preview


class Command(BaseCommand):
    help = "Generate PNG previews for resumes (first page thumbnail)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate previews even if they already exist",
        )

    def handle(self, *args, **options):
        force = options["force"]
        count = 0
        for resume in Resume.objects.all():
            if force or not getattr(resume.preview_image, "name", None):
                storage_path = generate_resume_preview(resume)
                if storage_path:
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f"Generated: {resume.pk} -> {storage_path}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Skipped/failed: {resume.pk}"))
        self.stdout.write(self.style.SUCCESS(f"Done. Generated {count} previews."))
