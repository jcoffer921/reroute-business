from django.db import models


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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_verified", "category"], name="reentry_org_is_verified_category_idx"),
        ]

    def __str__(self) -> str:
        return self.name

