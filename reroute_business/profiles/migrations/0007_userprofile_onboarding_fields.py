from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0006_userprofile_background_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="onboarding_step",
            field=models.CharField(
                blank=True,
                choices=[
                    ("start", "Start"),
                    ("profile_started", "Profile started"),
                    ("profile_completed", "Profile completed"),
                    ("resume_started", "Resume started"),
                    ("resume_completed", "Resume completed"),
                    ("completed", "Completed"),
                ],
                default="start",
                help_text="Current onboarding milestone for the seeker.",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="onboarding_completed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="early_access_priority",
            field=models.BooleanField(default=False),
        ),
    ]
