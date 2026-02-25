from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0006_agencypartnershipapplication_additional_eligibility_details_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="youtubevideo",
            name="duration_minutes",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Optional: duration shown on modules cards (minutes).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="youtubevideo",
            name="quiz_lesson_count",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Optional: lesson/quiz count shown on cards.",
                null=True,
            ),
        ),
    ]
