from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job_list', '0003_archivedjob'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='notes',
            field=models.TextField(blank=True),
        ),
    ]
