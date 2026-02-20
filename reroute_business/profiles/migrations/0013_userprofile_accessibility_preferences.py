from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0012_public_profile_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="low_data_mode",
            field=models.BooleanField(
                default=False,
                help_text="Reduce heavy media and animations for lower data usage.",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="preferred_language",
            field=models.CharField(
                default="en",
                help_text="Preferred UI language code (e.g. en, es).",
                max_length=8,
            ),
        ),
    ]
