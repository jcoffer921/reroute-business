from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Job, Application


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title", "employer", "location", "zip_code",
        "tags", "is_active", "created_at_display", "employer_image_preview", "salary_type"
    )
    list_filter = ("location", "zip_code", "employer", "is_active")
    search_fields = ("title", "employer__username", "location", "zip_code", "tags", "salary_type")

    # Custom display for created_at
    def created_at_display(self, obj):
        return obj.created_at.strftime("%b %d, %Y") if obj.created_at else "—"
    created_at_display.short_description = "Posted"

    # Optional: Show a small preview of the logo in admin
    def employer_image_preview(self, obj):
        try:
            url = getattr(obj.employer_image, 'url', None)
        except Exception:
            url = None
        if url:
            return mark_safe(
                f'<img src="{url}" width="40" height="40" style="object-fit:cover;border-radius:4px;" />'
            )
        return "—"
    employer_image_preview.short_description = "Logo"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job", "applicant", "status", "submitted_at_display")
    list_filter = ("status", "job", "submitted_at")
    search_fields = ("job__title", "applicant__username")

    def submitted_at_display(self, obj):
        return obj.submitted_at.strftime("%b %d, %Y") if obj.submitted_at else "—"
    submitted_at_display.short_description = "Submitted"
