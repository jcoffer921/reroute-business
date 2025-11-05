from django.db import migrations


def add_quick_tip(apps, schema_editor):
    YouTubeVideo = apps.get_model('main', 'YouTubeVideo')
    mp4 = '/static/resources/videos/dontSayInInterview.mp4'
    poster = '/static/images/dont_say_interview.png'

    # Avoid duplicates by mp4 path or title
    exists = YouTubeVideo.objects.filter(mp4_static_path=mp4).exists()
    if exists:
        return

    YouTubeVideo.objects.create(
        title="Quick Tip – 5 Things to Never Say in an Interview",
        video_url="",
        mp4_static_path=mp4,
        poster=poster,
        category="quick",
        tags="interview,tips,quick",
        description="A 1-minute tip covering common interview mistakes and what to say instead.",
    )


def remove_quick_tip(apps, schema_editor):
    YouTubeVideo = apps.get_model('main', 'YouTubeVideo')
    YouTubeVideo.objects.filter(mp4_static_path='/static/resources/videos/dontSayInInterview.mp4').delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_youtubevideo_mp4_poster"),
    ]

    operations = [
        migrations.RunPython(add_quick_tip, remove_quick_tip),
    ]

