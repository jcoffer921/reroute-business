from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0002_youtubevideo_category_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="youtubevideo",
            name="mp4_static_path",
            field=models.CharField(blank=True, default="", help_text="Optional: local MP4 under /static, e.g. /static/resources/videos/quick_tip.mp4", max_length=500),
        ),
        migrations.AddField(
            model_name="youtubevideo",
            name="poster",
            field=models.CharField(blank=True, default="", help_text="Optional: poster image path under /static for local MP4s", max_length=500),
        ),
    ]

