from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0005_add_background_image_to_employerprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='background_image',
            field=models.ImageField(blank=True, null=True, upload_to='users/backgrounds/'),
        ),
    ]

