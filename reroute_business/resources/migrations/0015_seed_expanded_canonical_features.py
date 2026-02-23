from django.db import migrations


CANONICAL_FEATURES = [
    ("spanish_available", "Spanish Available"),
    ("bilingual_staff", "Bilingual Staff"),
    ("culturally_specific", "Culturally Specific"),
    ("lgbtq_affirming", "LGBTQ+ Affirming"),
    ("trauma_informed", "Trauma-Informed"),
    ("justice_impacted_staff", "Justice-Impacted Staff"),
    ("free_services", "Free Services"),
    ("sliding_scale", "Sliding Scale Fees"),
    ("no_insurance_required", "No Insurance Required"),
    ("accepts_medicaid", "Accepts Medicaid"),
    ("no_id_required", "ID Not Required to Start Services"),
    ("remote_services", "Remote Services"),
    ("near_public_transit", "Near Public Transit"),
    ("walk_ins", "Walk-Ins Accepted"),
    ("same_day_services", "Same-Day Services Available"),
    ("appointment_required", "Appointment Required"),
    ("childcare_support", "Childcare Support"),
    ("court_approved", "Court-Approved Program"),
]


def forwards(apps, schema_editor):
    Feature = apps.get_model("resources", "Feature")
    ResourceOrganization = apps.get_model("resources", "ResourceOrganization")

    features_by_slug = {}
    for slug, label in CANONICAL_FEATURES:
        feature, _ = Feature.objects.update_or_create(
            slug=slug,
            defaults={"label": label, "is_active": True},
        )
        features_by_slug[slug] = feature

    for resource in ResourceOrganization.objects.all():
        legacy = getattr(resource, "legacy_features", None) or []
        if not isinstance(legacy, (list, tuple)):
            continue
        for slug in legacy:
            slug = str(slug).strip()
            feature = features_by_slug.get(slug)
            if feature:
                resource.features.add(feature)


def backwards(apps, schema_editor):
    Feature = apps.get_model("resources", "Feature")
    slugs = [slug for slug, _ in CANONICAL_FEATURES]
    Feature.objects.filter(slug__in=slugs).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0014_expand_resourceorganization_category_choices"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
