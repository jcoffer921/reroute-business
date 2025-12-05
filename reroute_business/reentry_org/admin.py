from django.contrib import admin

from .models import ReentryOrganization, SavedOrganization


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
