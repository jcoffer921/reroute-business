from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0004_resourcemodule_video_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcemodule',
            name='quiz_data',
            field=models.JSONField(blank=True, null=True),
        ),
    ]

