from django.db import migrations, models


def seed_gallery_category(apps, schema_editor):
    Module = apps.get_model("resources", "Module")

    keyword_map = [
        ("ids_documents", ("id", "license", "birth certificate", "document", "social security", "ssn")),
        ("jobs_interviews", ("job", "interview", "resume", "cover letter", "work", "career")),
        ("housing", ("housing", "rent", "apartment", "shelter", "lease")),
        ("benefits", ("benefit", "snap", "medicaid", "assistance", "support program")),
        ("transportation", ("transport", "bus", "train", "septa", "commute")),
        ("health_mental_health", ("health", "mental", "therapy", "wellness", "stress", "anxiety")),
        ("financial_basics", ("finance", "budget", "bank", "credit", "money", "debt", "savings")),
    ]

    legacy_defaults = {
        "workforce": "jobs_interviews",
        "digital": "financial_basics",
        "reentry": "ids_documents",
        "life": "health_mental_health",
    }

    for module in Module.objects.all().only("id", "title", "description", "category"):
        text = f"{(module.title or '').lower()} {(module.description or '').lower()}"
        chosen = None
        for cat_slug, keywords in keyword_map:
            if any(kw in text for kw in keywords):
                chosen = cat_slug
                break

        if not chosen:
            chosen = legacy_defaults.get((module.category or "").strip().lower(), "jobs_interviews")

        Module.objects.filter(pk=module.pk).update(gallery_category=chosen)


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0020_alter_resourceorganization_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="module",
            name="gallery_category",
            field=models.CharField(
                choices=[
                    ("ids_documents", "IDs & Documents"),
                    ("jobs_interviews", "Jobs & Interviews"),
                    ("housing", "Housing"),
                    ("benefits", "Benefits"),
                    ("transportation", "Transportation"),
                    ("health_mental_health", "Health & Mental Health"),
                    ("financial_basics", "Financial Basics"),
                ],
                default="jobs_interviews",
                max_length=50,
            ),
        ),
        migrations.RunPython(seed_gallery_category, migrations.RunPython.noop),
    ]
