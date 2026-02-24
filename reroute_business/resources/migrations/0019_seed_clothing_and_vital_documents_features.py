from django.db import migrations


FEATURES = [
    ("clothing", "Clothing"),
    ("vital_documents", "Vital Documents"),
]


def forwards(apps, schema_editor):
    Feature = apps.get_model("resources", "Feature")
    for slug, label in FEATURES:
        Feature.objects.update_or_create(
            slug=slug,
            defaults={"label": label, "is_active": True},
        )


def backwards(apps, schema_editor):
    Feature = apps.get_model("resources", "Feature")
    Feature.objects.filter(slug__in=[slug for slug, _ in FEATURES]).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0018_resourceorganization_is_verified"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
