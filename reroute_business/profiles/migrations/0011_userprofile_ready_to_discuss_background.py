from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0010_employerprofile_company_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='ready_to_discuss_background',
            field=models.BooleanField(default=False, help_text='User-controlled toggle for employers to see readiness to discuss background.'),
        ),
    ]
