from django.core.management.base import BaseCommand
from core.models import Skill
from core.constants import RELATABLE_SKILLS

class Command(BaseCommand):
    help = 'Seeds the Skill table with relatable skills from constants.py'

    def handle(self, *args, **kwargs):
        created = 0
        skipped = 0

        for skill_name in RELATABLE_SKILLS:
            skill_name = skill_name.strip()
            if skill_name:
                obj, was_created = Skill.objects.get_or_create(name=skill_name)
                if was_created:
                    created += 1
                else:
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded skills. Created: {created}, Skipped (already exist): {skipped}'
        ))
