from django.db import migrations, models
from django.utils.text import slugify


LEGACY_KEY_TO_LABEL = {
    "spanish_available": "Spanish Available",
    "bilingual_staff": "Bilingual Staff",
    "trauma_informed": "Trauma-Informed",
    "justice_impacted_staff": "Justice-Impacted Staff",
    "culturally_specific": "Culturally Specific",
    "remote_services": "Remote Services",
    "near_public_transit": "Near Public Transit",
    "childcare_support": "Childcare Support",
    "walk_ins": "Walk-Ins Accepted",
}


def _normalize_slug(value):
    if not value:
        return ""

    raw = str(value).strip()
    if not raw:
        return ""

    key = raw.lower().strip()
    if key in LEGACY_KEY_TO_LABEL:
        return key

    label_to_key = {label.lower(): slug for slug, label in LEGACY_KEY_TO_LABEL.items()}
    if key in label_to_key:
        return label_to_key[key]

    return slugify(raw).replace("-", "_")


def _label_for_value(value, slug_value):
    raw = str(value).strip() if value is not None else ""
    if slug_value in LEGACY_KEY_TO_LABEL:
        return LEGACY_KEY_TO_LABEL[slug_value]
    return raw or slug_value.replace("_", " ").title()


def migrate_legacy_features_to_m2m(apps, schema_editor):
    ResourceOrganization = apps.get_model("resources", "ResourceOrganization")
    Feature = apps.get_model("resources", "Feature")

    for resource in ResourceOrganization.objects.all():
        raw_values = getattr(resource, "legacy_features", None) or []
        if not isinstance(raw_values, (list, tuple)):
            continue

        for raw_value in raw_values:
            normalized_slug = _normalize_slug(raw_value)
            if not normalized_slug:
                continue

            defaults = {
                "label": _label_for_value(raw_value, normalized_slug),
                "is_active": True,
            }
            feature, created = Feature.objects.get_or_create(slug=normalized_slug, defaults=defaults)
            if not created and not feature.label:
                feature.label = defaults["label"]
                feature.save(update_fields=["label"])

            resource.features.add(feature)


def reverse_migrate_legacy_features_to_m2m(apps, schema_editor):
    ResourceOrganization = apps.get_model("resources", "ResourceOrganization")
    for resource in ResourceOrganization.objects.all():
        resource.features.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0010_resourceorganization"),
    ]

    operations = [
        migrations.CreateModel(
            name="Feature",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("label", models.CharField(max_length=80)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["label"]},
        ),
        migrations.RenameField(
            model_name="resourceorganization",
            old_name="features",
            new_name="legacy_features",
        ),
        migrations.AddField(
            model_name="resourceorganization",
            name="features",
            field=models.ManyToManyField(blank=True, related_name="resources", to="resources.feature"),
        ),
        migrations.RunPython(migrate_legacy_features_to_m2m, reverse_migrate_legacy_features_to_m2m),
    ]
