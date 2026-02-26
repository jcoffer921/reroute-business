from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0023_align_module_category_with_gallery"),
    ]

    operations = [
        migrations.AddField(
            model_name="resourceorganization",
            name="additional_locations",
            field=models.ManyToManyField(
                blank=True,
                help_text="Optional: related org/service locations to show on detail pages.",
                related_name="location_references",
                to="resources.resourceorganization",
            ),
        ),
    ]
