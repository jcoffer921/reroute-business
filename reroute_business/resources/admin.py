from django.contrib import admin
from .models import ResourceModule


@admin.register(ResourceModule)
class ResourceModuleAdmin(admin.ModelAdmin):
    """
    Admin configuration to manage Learning Modules.
    - Search by title and description for quick discovery.
    - Filter by category to narrow down content.
    - Default ordering shows most recent first.
    """

    list_display = ("title", "category", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "description")
    ordering = ("-created_at",)
