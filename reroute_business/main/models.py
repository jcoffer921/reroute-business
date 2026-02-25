from django.db import models
from django.contrib.auth.models import User
from urllib.parse import urlparse, parse_qs


class YouTubeVideo(models.Model):
    title = models.CharField(max_length=200)
    video_url = models.URLField(
        help_text=(
            "Paste a YouTube URL, e.g., https://www.youtube.com/watch?v=VIDEO_ID or https://youtu.be/VIDEO_ID"
        )
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    CATEGORY_CHOICES = [
        ("module", "Module (Interactive)"),
        ("quick", "Quick Tip"),
        ("lecture", "Lecture"),
        ("webinar", "Webinar"),
        ("other", "Other"),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, blank=True, default="")
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional: duration shown on modules cards (minutes).",
    )
    quiz_lesson_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional: lesson/quiz count shown on cards.",
    )
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags, e.g., resume,interview,soft-skills")
    mp4_static_path = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Optional: local MP4 under /static, e.g. /static/resources/videos/quick_tip.mp4"
    )
    poster = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Optional: poster image path under /static for local MP4s"
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title

    def embed_url(self) -> str:
        """Return an embeddable YouTube URL for this video."""
        val = (self.video_url or "").strip()
        if not val:
            return ""

        # Already an embed URL
        if "youtube.com/embed/" in val or "youtube-nocookie.com/embed/" in val:
            return val

        try:
            u = urlparse(val)
        except Exception:
            return val

        host = (u.netloc or "").lower()
        path = u.path or ""
        qs = parse_qs(u.query or "")

        def _append_enablejsapi(url: str) -> str:
            try:
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                u = urlparse(url)
                q = parse_qs(u.query)
                if "enablejsapi" not in q:
                    q["enablejsapi"] = ["1"]
                new_q = urlencode({k: v[-1] if isinstance(v, list) else v for k, v in q.items()})
                return urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))
            except Exception:
                return url

        # Helper to prefer nocookie embeds
        def _nocookie(url: str) -> str:
            try:
                from urllib.parse import urlparse, urlunparse
                u = urlparse(url)
                host = u.netloc.replace('www.youtube.com', 'www.youtube-nocookie.com').replace('youtube.com', 'youtube-nocookie.com')
                return urlunparse((u.scheme, host, u.path, u.params, u.query, u.fragment))
            except Exception:
                return url

        # youtu.be short links
        if host.endswith("youtu.be"):
            vid = path.lstrip("/").split("/")[0]
            return _append_enablejsapi(f"https://www.youtube-nocookie.com/embed/{vid}") if vid else val

        # youtube watch links
        if host.endswith("youtube.com") or host.endswith("m.youtube.com") or host.endswith("www.youtube.com"):
            if path.startswith("/watch"):
                vid = (qs.get("v") or [""])[0]
                return _append_enablejsapi(f"https://www.youtube-nocookie.com/embed/{vid}") if vid else val
            # shorts
            if "/shorts/" in path:
                parts = [p for p in path.split("/") if p]
                try:
                    i = parts.index("shorts")
                    vid = parts[i + 1]
                    return _append_enablejsapi(f"https://www.youtube-nocookie.com/embed/{vid}") if vid else val
                except Exception:
                    pass

        return val


class AgencyPartnershipApplication(models.Model):
    ORGANIZATION_TYPE_NONPROFIT = "nonprofit"
    ORGANIZATION_TYPE_FOR_PROFIT = "for_profit"
    ORGANIZATION_TYPE_GOVERNMENT = "government"
    ORGANIZATION_TYPE_CHOICES = [
        (ORGANIZATION_TYPE_NONPROFIT, "Nonprofit"),
        (ORGANIZATION_TYPE_FOR_PROFIT, "For-Profit"),
        (ORGANIZATION_TYPE_GOVERNMENT, "Government"),
    ]

    REFERRAL_METHOD_WEBSITE = "website_link"
    REFERRAL_METHOD_EMAIL = "email_referral"
    REFERRAL_METHOD_PHONE = "phone_referral"
    REFERRAL_METHOD_API = "api_future"
    REFERRAL_METHOD_CHOICES = [
        (REFERRAL_METHOD_WEBSITE, "Direct website link"),
        (REFERRAL_METHOD_EMAIL, "Email referral"),
        (REFERRAL_METHOD_PHONE, "Phone referral"),
        (REFERRAL_METHOD_API, "API integration (future)"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_IN_REVIEW = "in_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_IN_REVIEW, "In Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    organization_name = models.CharField(max_length=255, blank=True)
    primary_contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    physical_address = models.CharField(max_length=255, blank=True)
    service_area = models.CharField(
        max_length=255,
        blank=True,
        help_text="City / ZIP coverage",
    )
    year_founded = models.PositiveIntegerField(null=True, blank=True)
    organization_type = models.CharField(
        max_length=32,
        choices=ORGANIZATION_TYPE_CHOICES,
        blank=True,
    )

    services_offered = models.JSONField(default=list, blank=True)
    services_other = models.CharField(max_length=255, blank=True)

    target_population = models.JSONField(default=list, blank=True)
    target_population_other = models.CharField(max_length=255, blank=True)
    supports_justice_impacted = models.BooleanField(default=False)
    supports_recently_released = models.BooleanField(default=False)
    requires_government_id = models.BooleanField(default=False)
    requires_release_window = models.BooleanField(default=False)
    requires_orientation_attendance = models.BooleanField(default=False)
    requires_intake_assessment = models.BooleanField(default=False)
    requires_service_area_residency = models.BooleanField(default=False)
    additional_eligibility_details = models.TextField(blank=True)

    average_served_per_month = models.PositiveIntegerField(null=True, blank=True)
    intake_process_description = models.TextField(blank=True)
    referral_method_preference = models.CharField(
        max_length=32,
        choices=REFERRAL_METHOD_CHOICES,
        blank=True,
    )
    tracks_employment_outcomes = models.BooleanField(null=True, blank=True)
    open_to_referral_tracking = models.BooleanField(null=True, blank=True)

    partnership_reason = models.TextField(blank=True)
    reroute_support_needs = models.TextField(blank=True)
    interested_in_featured_verified = models.BooleanField(null=True, blank=True)

    accuracy_confirmation = models.BooleanField(default=False)
    terms_privacy_agreement = models.BooleanField(default=False)
    logo = models.ImageField(upload_to="partner_logos/", null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_agency_applications",
    )
    internal_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.organization_name or f"Agency Application #{self.pk}"


