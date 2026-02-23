from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.conf import settings


class ReentryOrganization(models.Model):
    CATEGORIES = (
        ("employment", "Employment"),
        ("education", "Education"),
        ("housing", "Housing"),
        ("legal", "Legal"),
        ("health", "Health"),
        ("mentorship", "Mentorship"),
        ("financial", "Financial"),
        ("family", "Family & Children"),
        ("transportation", "Transportation"),
        ("other", "Other"),
    )

    name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=32, choices=CATEGORIES, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)

    logo = models.ImageField(upload_to="org_logos/", blank=True, null=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)

    city = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=64, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    geo_point = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            # Short index name to satisfy backends with 30-char identifier limits (e.g., Oracle)
            models.Index(fields=["is_verified", "category"], name="reorg_vrf_cat_idx"),
            GistIndex(fields=["geo_point"]),
        ]

    def __str__(self) -> str:
        return self.name


class SavedOrganization(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_organizations")
    organization = models.ForeignKey(ReentryOrganization, on_delete=models.CASCADE, related_name="saves")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "organization")
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.user} saved {self.organization}"
