from django.core.management.base import BaseCommand

from reroute_business.resources.legacy_quiz import convert_module_legacy_quiz
from reroute_business.resources.models import Module


class Command(BaseCommand):
    help = "Convert legacy Module.quiz_data questions into relational QuizQuestion/QuizAnswer records."

    def add_arguments(self, parser):
        parser.add_argument("--module-id", type=int, dest="module_id")

    def handle(self, *args, **options):
        module_id = options.get("module_id")
        queryset = Module.objects.all().order_by("id")
        if module_id:
            queryset = queryset.filter(id=module_id)

        converted_modules = 0
        converted_questions = 0
        for module in queryset:
            if module.questions.exists():
                continue
            count = convert_module_legacy_quiz(module)
            if count:
                converted_modules += 1
                converted_questions += count
                self.stdout.write(f"Converted module {module.id}: {count} questions")

        self.stdout.write(
            self.style.SUCCESS(
                f"Converted {converted_questions} questions across {converted_modules} module(s)."
            )
        )
