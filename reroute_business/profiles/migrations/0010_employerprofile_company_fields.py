from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0009_userprofile_background_gradient'),
    ]

    operations = [
        migrations.AddField(
            model_name='employerprofile',
            name='company_size',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='employerprofile',
            name='fair_chance_statement',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='employerprofile',
            name='industry',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='employerprofile',
            name='logo_url',
            field=models.URLField(blank=True),
        ),
    ]
