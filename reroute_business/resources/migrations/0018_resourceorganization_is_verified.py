from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0017_resourceorganization_geo_point_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="resourceorganization",
            name="is_verified",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
