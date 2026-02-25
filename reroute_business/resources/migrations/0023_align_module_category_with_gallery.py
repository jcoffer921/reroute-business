from django.db import migrations, models


def remap_legacy_module_categories(apps, schema_editor):
    Module = apps.get_model("resources", "Module")
    mapping = {
        "workforce": "jobs_interviews",
        "digital": "financial_basics",
        "reentry": "ids_documents",
        "life": "health_mental_health",
    }

    for old_value, new_value in mapping.items():
        Module.objects.filter(category=old_value).update(category=new_value)


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0022_module_duration_and_quiz_lesson_count"),
    ]

    operations = [
        migrations.RunPython(remap_legacy_module_categories, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="module",
            name="category",
            field=models.CharField(
                choices=[
                    ("ids_documents", "IDs & Documents"),
                    ("jobs_interviews", "Jobs & Interviews"),
                    ("housing", "Housing"),
                    ("benefits", "Benefits"),
                    ("transportation", "Transportation"),
                    ("health_mental_health", "Health & Mental Health"),
                    ("financial_basics", "Financial Basics"),
                ],
                max_length=50,
            ),
        ),
    ]
