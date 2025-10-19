from django.contrib import admin

from .models import AnalyticsEvent, Skill, SuggestedSkill


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    """Admin list for quick filtering and counts."""
    list_display = ("event_type", "path", "user", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("path", "user__username", "user__email")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(SuggestedSkill)
class SuggestedSkillAdmin(admin.ModelAdmin):
    list_display = ("name", "approved", "added_by", "created_at")
    list_filter = ("approved", "created_at")
    search_fields = ("name", "added_by__username")
