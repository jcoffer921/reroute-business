from django.db import migrations


def forward(apps, schema_editor):
    LegacyApplication = apps.get_model("resumes", "Application")
    JobApplication = apps.get_model("job_list", "Application")

    valid_statuses = {"pending", "reviewed", "interview", "rejected", "accepted"}

    for legacy in LegacyApplication.objects.all().order_by("id").iterator():
        status = (legacy.status or "pending").strip().lower()
        if status not in valid_statuses:
            status = "pending"

        existing = JobApplication.objects.filter(applicant_id=legacy.applicant_id, job_id=legacy.job_id).first()
        if existing:
            if existing.status == "pending" and status != "pending":
                existing.status = status
                existing.save(update_fields=["status", "updated_at"])
            continue

        JobApplication.objects.create(
            applicant_id=legacy.applicant_id,
            job_id=legacy.job_id,
            status=status,
            notes="Migrated from resumes.Application",
        )


def backward(apps, schema_editor):
    # No-op: preserve backfilled job applications.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("resumes", "0007_alter_educationtype_id_alter_resumeskill_id"),
        ("job_list", "0005_jobinvitation"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
