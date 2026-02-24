# Generated manually for PostGIS + geo matching support.
from django.db import migrations, models

try:
    from django.contrib.gis.db.models import fields as gis_fields
except Exception:
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
        ("job_list", "0007_rename_job_list_j_employe_96c1db_idx_job_list_jo_employe_e9eba9_idx_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS postgis;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AddField(
            model_name="job",
            name="geo_point",
            field=gis_fields.PointField(blank=True, geography=True, null=True, srid=4326),
        ),
        migrations.CreateModel(
            name="ZipCentroid",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("zip_code", models.CharField(max_length=10, unique=True)),
                ("geo_point", gis_fields.PointField(geography=True, srid=4326)),
            ],
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(fields=["geo_point"], name="job_list_jo_geo_p_681e90_idx"),
        ),
        migrations.AddIndex(
            model_name="zipcentroid",
            index=models.Index(fields=["geo_point"], name="job_list_zi_geo_p_3a6fa1_idx"),
        ),
    ]
