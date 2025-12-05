from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reentry_org", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedOrganization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="saves", to="reentry_org.reentryorganization"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="saved_organizations", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
                "unique_together": {("user", "organization")},
            },
        ),
    ]

