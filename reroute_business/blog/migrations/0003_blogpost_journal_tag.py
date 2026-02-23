from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0002_blogpost_owner_blogpost_updated_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogpost",
            name="journal_tag",
            field=models.CharField(
                blank=True,
                choices=[
                    ("interview", "Interview"),
                    ("job_search", "Job Search"),
                    ("confidence", "Confidence"),
                    ("training", "Training"),
                    ("personal_growth", "Personal Growth"),
                ],
                max_length=32,
            ),
        ),
    ]
