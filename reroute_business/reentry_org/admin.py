from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import ReentryOrganization, SavedOrganization, ReentryOrgApplication


@admin.register(ReentryOrganization)
class ReentryOrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_verified", "city", "state", "created_at")
    list_filter = ("is_verified", "category", "state")
    search_fields = ("name", "description", "city", "state")
    ordering = ("name",)
    list_editable = ("is_verified",)


@admin.register(SavedOrganization)
class SavedOrganizationAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "created_at")
    search_fields = ("user__username", "organization__name")
    list_filter = ("organization__category",)


@admin.register(ReentryOrgApplication)
class ReentryOrgApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "public_application_id",
        "org_name",
        "contact_email",
        "status",
        "submitted_at",
        "download_pdf_link",
    )
    list_filter = ("status", "organization_type", "submitted_at")
    search_fields = ("org_name", "contact_email", "service_area", "primary_contact_name")
    readonly_fields = ("application_id", "submitted_at", "reviewed_at", "download_pdf_detail_link")
    actions = ("mark_approved", "mark_rejected")

    fieldsets = (
        ("Admin", {"fields": ("application_id", "status", "reviewed_by", "reviewed_at", "submitted_at", "download_pdf_detail_link")}),
        ("Step 1 — Organization Information", {"fields": (
            "org_name", "primary_contact_name", "contact_email", "contact_phone",
            "website", "physical_address", "service_area", "year_founded", "organization_type",
        )}),
        ("Step 2 — Services", {"fields": ("services", "other_services")}),
        ("Step 3 — Population + Program Criteria", {"fields": (
            "serve_justice_impacted", "serve_recently_released", "additional_populations", "other_populations",
            "program_criteria", "requires_id", "requires_orientation", "requires_intake_assessment",
            "requires_residency_in_service_area",
        )}),
        ("Step 4 — Capacity & Operations", {"fields": (
            "avg_served_per_month", "intake_process_description", "preferred_referral_method",
            "tracks_employment_outcomes", "open_to_referral_tracking",
        )}),
        ("Step 5 — Partnership Alignment", {"fields": (
            "why_partner", "how_reroute_can_support", "interested_featured_verified",
        )}),
        ("Step 6 — Compliance & Consent", {"fields": (
            "accuracy_confirmation", "terms_privacy_agreement", "logo",
        )}),
    )

    @admin.display(description="PDF")
    def download_pdf_link(self, obj):
        url = reverse("reentry_org:application_pdf", args=[obj.pk])
        return format_html('<a class="button" href="{}">Download PDF</a>', url)

    @admin.display(description="Application ID")
    def public_application_id(self, obj):
        return obj.public_application_id

    @admin.display(description="Download PDF")
    def download_pdf_detail_link(self, obj):
        if not obj or not obj.pk:
            return "-"
        url = reverse("reentry_org:application_pdf", args=[obj.pk])
        return format_html('<a class="button" href="{}">Download PDF</a>', url)

    @admin.action(description="Mark selected applications as approved")
    def mark_approved(self, request, queryset):
        queryset.update(
            status=ReentryOrgApplication.STATUS_APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )

    @admin.action(description="Mark selected applications as rejected")
    def mark_rejected(self, request, queryset):
        queryset.update(
            status=ReentryOrgApplication.STATUS_REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
