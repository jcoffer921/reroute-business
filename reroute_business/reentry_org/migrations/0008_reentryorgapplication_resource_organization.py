from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0023_align_module_category_with_gallery"),
        ("reentry_org", "0007_reentryorgapplication_application_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="reentryorgapplication",
            name="resource_organization",
            field=models.ForeignKey(
                blank=True,
                help_text="Linked Resource Organization record created/updated from this application.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_applications",
                to="resources.resourceorganization",
            ),
        ),
    ]
