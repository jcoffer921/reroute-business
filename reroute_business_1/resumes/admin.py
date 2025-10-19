from django.contrib import admin
from .models import Resume
from .utils.summaries import random_generic_summary


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_imported", "created_at", "updated_at")
    list_filter = ("is_imported", "created_at")
    search_fields = ("user__username", "user__email", "full_name")
    actions = ("regenerate_generic_summary",)

    @admin.action(description="Regenerate generic professional summary")
    def regenerate_generic_summary(self, request, queryset):
        updated = 0
        for resume in queryset:
            resume.summary = random_generic_summary()
            resume.save(update_fields=["summary"])
            updated += 1
        self.message_user(request, f"Regenerated summary for {updated} resume(s).")
