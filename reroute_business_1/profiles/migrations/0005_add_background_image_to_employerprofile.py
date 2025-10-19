from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0004_employerprofile_verification_notes_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employerprofile',
            name='background_image',
            field=models.ImageField(blank=True, null=True, upload_to='employers/backgrounds/'),
        ),
    ]

