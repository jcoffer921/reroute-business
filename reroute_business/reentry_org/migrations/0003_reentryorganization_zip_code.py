from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reentry_org", "0002_savedorganization"),
    ]

    operations = [
        migrations.AddField(
            model_name="reentryorganization",
            name="zip_code",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
