from django.core.management.base import BaseCommand

# Import the ResourceModule model used for Learning Modules
from reroute_business.resources.models import ResourceModule


class Command(BaseCommand):
    """
    Seed example ResourceModule cards without external embeds.

    Removes legacy Edpuzzle usage by leaving `embed_html` empty so the
    Resources page shows native lessons only (or a Coming Soon placeholder).
    Safe to run multiple times.
    """

    help = "Seed demo ResourceModule cards without external embeds."

    def handle(self, *args, **options):
        # Optional internal notes/content for future expansion
        internal_notes = (
            "Understand what employers look for in interviews\n"
            "Practice concise storytelling using the STAR method (Situation, Task, Action, Result)\n"
            "Build confidence through mock questions\n"
            "Learn effective follow-up etiquette\n"
        )

        # Interview Prep 101 card without external embed
        obj, created = ResourceModule.objects.update_or_create(
            title="Interview Prep 101",
            defaults={
                "category": ResourceModule.CATEGORY_WORKFORCE,
                "description": (
                    "Learn how to prepare for your next interview with confidence. "
                    "Covers research, common questions, and how to leave a strong impression."
                ),
                # No video yet; placeholder only
                "video_url": "",
                "embed_html": "",
                "internal_content": internal_notes,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                "Created ResourceModule: 'Interview Prep 101'"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "Updated ResourceModule: 'Interview Prep 101'"
            ))

        # Resume Basics 101 card without external embed; interactive lesson is separate
        obj2, created2 = ResourceModule.objects.update_or_create(
            title="Resume Basics 101",
            defaults={
                "category": ResourceModule.CATEGORY_WORKFORCE,
                "description": (
                    "Build a strong resume that highlights your skills and experience. "
                    "This quick lesson covers structure, strong statements, and soft skills."
                ),
                # Use watch URL; template converts to embed automatically
                "video_url": "https://www.youtube.com/watch?v=bBkWA7sBOEg",
                "embed_html": "",
                "internal_content": (
                    "Focus on accomplishments, tailor for each job, and keep it concise.\n"
                    "Use action verbs and quantify results where possible.\n"
                ),
            },
        )

        if created2:
            self.stdout.write(self.style.SUCCESS(
                "Created ResourceModule: 'Resume Basics 101'"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "Updated ResourceModule: 'Resume Basics 101'"
            ))

        # Local MP4 module: What Not to Say in an Interview
        obj3, created3 = ResourceModule.objects.update_or_create(
            title="What Not to Say in an Interview",
            defaults={
                "category": ResourceModule.CATEGORY_WORKFORCE,
                "description": (
                    "A quick 1-minute tip on common interview mistakes and better alternatives."
                ),
                # Static path is served by WhiteNoise/app staticfiles
                "video_url": "/static/resources/videos/dontSayInInterview.mp4",
                "embed_html": "",
            },
        )

        if created3:
            self.stdout.write(self.style.SUCCESS(
                "Created ResourceModule: 'What Not to Say in an Interview'"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "Updated ResourceModule: 'What Not to Say in an Interview'"
            ))

        self.stdout.write(self.style.SUCCESS(
            "Seed complete. Visit /resources/ to view the modules and videos."
        ))
