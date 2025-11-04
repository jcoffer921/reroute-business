from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0003_lesson_youtube_video_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="resourcemodule",
            name="video_url",
            field=models.CharField(blank=True, null=True, max_length=500),
        ),
    ]

