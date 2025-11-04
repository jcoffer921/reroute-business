from django.core.management.base import BaseCommand

# Import the ResourceModule model used for Learning Modules
from reroute_business.resources.models import ResourceModule


class Command(BaseCommand):
    """
    Seed a demo Learning Module for inline playback on the Resources page.

    This command creates or updates the "Interview Preparation Basics" module
    with an Edpuzzle iframe stored in `embed_html`. It is safe to run multiple
    times; subsequent runs will update the existing record.
    """

    help = "Seed a demo ResourceModule with inline Edpuzzle video (no redirects)."

    def handle(self, *args, **options):
        # Admin-provided embed code to render inline (iframe is stored as HTML)
        embed_iframe = (
            '<iframe width="590" height="475" '
            'src="https://edpuzzle.com/embed/media/68e722221dd3288ee3765820" '
            'frameborder="0" allowfullscreen></iframe>'
        )

        # Optional internal notes/content for future expansion
        internal_notes = (
            "Understand what employers look for in interviews\n"
            "Practice concise storytelling using the STAR method (Situation, Task, Action, Result)\n"
            "Build confidence through mock questions\n"
            "Learn effective follow-up etiquette\n"
        )

        # Create or update the ResourceModule by title to keep this idempotent
        obj, created = ResourceModule.objects.update_or_create(
            title="Interview Preparation Basics",
            defaults={
                "category": ResourceModule.CATEGORY_WORKFORCE,  # Workforce Readiness
                "description": (
                    "Learn how to prepare for your next interview with confidence. "
                    "This short lesson covers how to research the company, practice common questions, "
                    "and leave a lasting impression. Includes real-world examples and quick tips to help "
                    "you stand out in any hiring conversation."
                ),
                "embed_html": embed_iframe,   # Inline player (no external redirects)
                "internal_content": internal_notes,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                "Created demo ResourceModule: 'Interview Preparation Basics'"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "Updated existing ResourceModule: 'Interview Preparation Basics'"
            ))

        self.stdout.write(self.style.SUCCESS(
            "Seed complete. Visit /resources/ to view the Learning Modules section."
        ))

