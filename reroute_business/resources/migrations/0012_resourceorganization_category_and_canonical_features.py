from django.db import migrations, models


CATEGORY_LABEL_TO_KEY = {
    "housing": "housing",
    "food": "food",
    "id/documents": "id_documents",
    "financial assistance": "financial_assistance",
    "benefits": "benefits",
    "childcare": "childcare",
    "healthcare (medical)": "healthcare",
    "healthcare": "healthcare",
    "mental health": "mental_health",
    "substance use treatment": "substance_use",
    "health & wellness": "wellness",
    "job training": "job_training",
    "legal aid": "legal",
    "legal_aid": "legal",
    "reentry organizations": "reentry_orgs",
    "reentry orgs": "reentry_orgs",
    "case management / navigation": "case_management",
    "multi-service agency": "multi_service",
    "government agencies": "govt_agencies",
    "education & literacy": "education",
    "career services": "career_services",
    "workforce development": "workforce_dev",
    "other": "other",
}

CANONICAL_FEATURES = [
    ("spanish_available", "Spanish Available"),
    ("bilingual_staff", "Bilingual Staff"),
    ("trauma_informed", "Trauma-Informed"),
    ("justice_impacted_staff", "Justice-Impacted Staff"),
    ("culturally_specific", "Culturally Specific"),
    ("remote_services", "Remote Services"),
    ("near_public_transit", "Near Public Transit"),
    ("childcare_support", "Childcare Support"),
    ("walk_ins", "Walk-Ins Accepted"),
]


def _normalize_category(raw_value):
    if not raw_value:
        return "other"
    key = str(raw_value).strip().lower()
    return CATEGORY_LABEL_TO_KEY.get(key, key if key in CATEGORY_LABEL_TO_KEY.values() else "other")


def forwards(apps, schema_editor):
    ResourceOrganization = apps.get_model("resources", "ResourceOrganization")
    Feature = apps.get_model("resources", "Feature")

    feature_by_slug = {}
    for slug, label in CANONICAL_FEATURES:
        feature, _ = Feature.objects.update_or_create(
            slug=slug,
            defaults={"label": label, "is_active": True},
        )
        feature_by_slug[slug] = feature

    for resource in ResourceOrganization.objects.all():
        category_value = "other"
        raw_categories = getattr(resource, "categories", None) or []
        if isinstance(raw_categories, (list, tuple)) and raw_categories:
            category_value = _normalize_category(raw_categories[0])
        resource.category = category_value
        resource.save(update_fields=["category"])

        legacy_features = getattr(resource, "legacy_features", None) or []
        if isinstance(legacy_features, (list, tuple)):
            for slug in legacy_features:
                slug = str(slug).strip()
                feature = feature_by_slug.get(slug)
                if feature:
                    resource.features.add(feature)


def backwards(apps, schema_editor):
    ResourceOrganization = apps.get_model("resources", "ResourceOrganization")

    for resource in ResourceOrganization.objects.all():
        category = getattr(resource, "category", "") or "other"
        label = category.replace("_", " ").title()
        if category == "id_documents":
            label = "ID/Documents"
        elif category == "reentry_orgs":
            label = "Reentry Organizations"
        elif category == "legal":
            label = "Legal Aid"
        elif category == "job_training":
            label = "Job Training"
        elif category == "mental_health":
            label = "Mental Health"
        elif category == "financial_assistance":
            label = "Financial Assistance"
        elif category == "substance_use":
            label = "Substance Use Treatment"
        elif category == "wellness":
            label = "Health & Wellness"
        elif category == "case_management":
            label = "Case Management / Navigation"
        elif category == "multi_service":
            label = "Multi-Service Agency"
        elif category == "govt_agencies":
            label = "Government Agencies"
        elif category == "education":
            label = "Education & Literacy"
        elif category == "career_services":
            label = "Career Services"
        elif category == "workforce_dev":
            label = "Workforce Development"
        resource.categories = [label]
        resource.save(update_fields=["categories"])


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0011_feature_model_and_resourceorganization_features_m2m"),
    ]

    operations = [
        migrations.AddField(
            model_name="resourceorganization",
            name="category",
            field=models.CharField(
                choices=[
                    ("housing", "Housing"),
                    ("id_documents", "ID/Documents"),
                    ("food", "Food"),
                    ("job_training", "Job Training"),
                    ("legal_aid", "Legal Aid"),
                    ("healthcare", "Healthcare"),
                    ("mental_health", "Mental Health"),
                    ("reentry_orgs", "Reentry Orgs"),
                    ("benefits", "Benefits"),
                    ("childcare", "Childcare"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=40,
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name="resourceorganization",
            name="categories",
        ),
    ]
