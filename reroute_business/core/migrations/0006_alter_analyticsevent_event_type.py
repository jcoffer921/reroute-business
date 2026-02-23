from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_rename_core_onboar_event_e79a28_idx_core_onboar_event_acd998_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="analyticsevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("page_view", "Page View"),
                    ("benefit_finder_event", "Benefit Finder Event"),
                    ("profile_view", "Profile View"),
                    ("profile_created", "Profile Created"),
                    ("profile_updated", "Profile Updated"),
                    ("profile_completed", "Profile Completed"),
                    ("resume_created", "Resume Created"),
                    ("resume_updated", "Resume Updated"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
    ]
