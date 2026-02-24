# Generated manually for PostGIS user profile support.
from django.conf import settings
from django.db import migrations, models

USE_GIS = bool(getattr(settings, "USE_GIS", False))

if USE_GIS:
    try:
        from django.contrib.gis.db.models import fields as gis_fields
    except Exception:
        USE_GIS = False

if not USE_GIS:
    class _PointField(models.TextField):
        def __init__(self, *args, **kwargs):
            kwargs.pop('geography', None)
            kwargs.pop('srid', None)
            super().__init__(*args, **kwargs)

    class _GISFields:
        PointField = _PointField

    gis_fields = _GISFields()


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
            field=gis_fields.PointField(blank=True, geography=True, null=True, srid=4326),
        ),
    ]
