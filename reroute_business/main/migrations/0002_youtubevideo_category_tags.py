from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="youtubevideo",
            name="category",
            field=models.CharField(blank=True, choices=[("module", "Module (Interactive)"), ("quick", "Quick Tip"), ("lecture", "Lecture"), ("webinar", "Webinar"), ("other", "Other")], default="", max_length=20),
        ),
        migrations.AddField(
            model_name="youtubevideo",
            name="tags",
            field=models.CharField(blank=True, help_text="Comma-separated tags, e.g., resume,interview,soft-skills", max_length=200),
        ),
    ]

