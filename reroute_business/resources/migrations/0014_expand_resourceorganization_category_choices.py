from django.db import migrations, models


OLD_TO_NEW_CATEGORY = {
    "legal_aid": "legal",
}


def remap_categories_forward(apps, schema_editor):
    ResourceOrganization = apps.get_model("resources", "ResourceOrganization")
    for resource in ResourceOrganization.objects.all():
        current = (resource.category or "").strip()
        updated = OLD_TO_NEW_CATEGORY.get(current, current or "other")
        if updated != current:
            resource.category = updated
            resource.save(update_fields=["category"])


def remap_categories_backward(apps, schema_editor):
    ResourceOrganization = apps.get_model("resources", "ResourceOrganization")
    reverse_map = {value: key for key, value in OLD_TO_NEW_CATEGORY.items()}
    for resource in ResourceOrganization.objects.all():
        current = (resource.category or "").strip()
        updated = reverse_map.get(current, current or "other")
        if updated != current:
            resource.category = updated
            resource.save(update_fields=["category"])


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0013_merge_20260222_1904"),
    ]

    operations = [
        migrations.RunPython(remap_categories_forward, remap_categories_backward),
        migrations.AlterField(
            model_name="resourceorganization",
            name="category",
            field=models.CharField(
                choices=[
                    ("housing", "Housing"),
                    ("food", "Food"),
                    ("id_documents", "ID/Documents"),
                    ("financial_assistance", "Financial Assistance"),
                    ("benefits", "Benefits"),
                    ("childcare", "Childcare"),
                    ("healthcare", "Healthcare (Medical)"),
                    ("mental_health", "Mental Health"),
                    ("substance_use", "Substance Use Treatment"),
                    ("wellness", "Health & Wellness"),
                    ("legal", "Legal Aid"),
                    ("reentry_orgs", "Reentry Organizations"),
                    ("case_management", "Case Management / Navigation"),
                    ("multi_service", "Multi-Service Agency"),
                    ("govt_agencies", "Government Agencies"),
                    ("education", "Education & Literacy"),
                    ("career_services", "Career Services"),
                    ("job_training", "Job Training"),
                    ("workforce_dev", "Workforce Development"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=40,
            ),
        ),
    ]
