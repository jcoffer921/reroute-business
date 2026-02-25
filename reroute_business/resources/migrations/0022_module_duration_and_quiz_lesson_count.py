from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0021_module_gallery_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="module",
            name="duration_minutes",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Optional: duration shown on module cards (minutes).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="module",
            name="quiz_lesson_count",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Optional: card lesson/quiz count override.",
                null=True,
            ),
        ),
    ]
