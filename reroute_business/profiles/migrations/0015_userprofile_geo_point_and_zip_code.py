# Generated manually for PostGIS user profile support.
from django.contrib.gis.db.models import fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0014_alter_profilecertification_id_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="zip_code",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="geo_point",
            field=fields.PointField(blank=True, geography=True, null=True, srid=4326),
        ),
    ]
