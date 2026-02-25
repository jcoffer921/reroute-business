from django.db import models
from django.contrib.postgres.indexes import GistIndex
from django.conf import settings
from django.contrib.auth import get_user_model
import uuid

if settings.USE_GIS:
    from django.contrib.gis.db import models as gis_models

User = get_user_model()


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
    if settings.USE_GIS:
        geo_point = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_verified", "name"]
        indexes = [
            # Short index name to satisfy backends with 30-char identifier limits (e.g., Oracle)
            models.Index(fields=["is_verified", "category"], name="reorg_vrf_cat_idx"),
        ]
        if settings.USE_GIS:
            indexes.append(GistIndex(fields=["geo_point"]))

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


class ReentryOrgApplication(models.Model):
    ORGANIZATION_TYPE_NONPROFIT = "nonprofit"
    ORGANIZATION_TYPE_FOR_PROFIT = "for_profit"
    ORGANIZATION_TYPE_GOVERNMENT = "government"
    ORGANIZATION_TYPE_CHOICES = [
        (ORGANIZATION_TYPE_NONPROFIT, "Nonprofit"),
        (ORGANIZATION_TYPE_FOR_PROFIT, "For-Profit"),
        (ORGANIZATION_TYPE_GOVERNMENT, "Government"),
    ]

    REFERRAL_METHOD_WEBSITE = "website"
    REFERRAL_METHOD_EMAIL = "email"
    REFERRAL_METHOD_PHONE = "phone"
    REFERRAL_METHOD_API_FUTURE = "api_future"
    REFERRAL_METHOD_CHOICES = [
        (REFERRAL_METHOD_WEBSITE, "Direct website link"),
        (REFERRAL_METHOD_EMAIL, "Email referral"),
        (REFERRAL_METHOD_PHONE, "Phone referral"),
        (REFERRAL_METHOD_API_FUTURE, "API integration (future)"),
    ]

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    application_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)

    # Step 1: Organization Information
    org_name = models.CharField(max_length=255, db_index=True)
    primary_contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField(db_index=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    physical_address = models.CharField(max_length=255, blank=True)
    service_area = models.CharField(max_length=255, blank=True, help_text="City / ZIP coverage")
    year_founded = models.PositiveIntegerField(null=True, blank=True)
    organization_type = models.CharField(max_length=32, choices=ORGANIZATION_TYPE_CHOICES, blank=True)

    # Step 2: Services
    services = models.JSONField(default=list, blank=True)
    other_services = models.CharField(max_length=255, blank=True)

    # Step 3: Population + Program Criteria
    serve_justice_impacted = models.BooleanField(default=False)
    serve_recently_released = models.BooleanField(default=False)
    additional_populations = models.JSONField(default=list, blank=True)
    other_populations = models.CharField(max_length=255, blank=True)
    program_criteria = models.TextField(blank=True)
    requires_id = models.BooleanField(default=False)
    requires_orientation = models.BooleanField(default=False)
    requires_intake_assessment = models.BooleanField(default=False)
    requires_residency_in_service_area = models.BooleanField(default=False)

    # Step 4: Capacity & Operations
    avg_served_per_month = models.PositiveIntegerField(null=True, blank=True)
    intake_process_description = models.TextField(blank=True)
    preferred_referral_method = models.CharField(max_length=32, choices=REFERRAL_METHOD_CHOICES, blank=True)
    tracks_employment_outcomes = models.BooleanField(null=True, blank=True)
    open_to_referral_tracking = models.BooleanField(null=True, blank=True)

    # Step 5: Partnership Alignment
    why_partner = models.TextField(blank=True)
    how_reroute_can_support = models.TextField(blank=True)
    interested_featured_verified = models.BooleanField(null=True, blank=True)

    # Step 6: Compliance & Consent
    accuracy_confirmation = models.BooleanField(default=False)
    terms_privacy_agreement = models.BooleanField(default=False)
    logo = models.ImageField(upload_to="reentry_org_application_logos/", null=True, blank=True)

    # Admin review metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_reentry_org_applications",
    )

    class Meta:
        ordering = ("-submitted_at", "-id")
        verbose_name = "Reentry Org Application"
        verbose_name_plural = "Reentry Org Applications"

    def __str__(self):
        return self.org_name

    @property
    def public_application_id(self):
        return f"RR-ORG-{str(self.application_id).split('-')[0].upper()}"
