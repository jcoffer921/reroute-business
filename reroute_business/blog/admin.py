from django.contrib import admin

from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "visibility", "category", "owner", "created_at", "updated_at")
    list_filter = ("visibility", "category", "published", "featured")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Content", {"fields": ("title", "content", "journal_tag", "image")}),
        (
            "Publishing",
            {
                "fields": (
                    "visibility",
                    "category",
                    "owner",
                    "slug",
                    "published",
                    "featured",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        # Staff users can only manage public story records in admin.
        return queryset.filter(visibility=BlogPost.VISIBILITY_PUBLIC)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        if not request.user.is_superuser:
            if "visibility" in form.base_fields:
                form.base_fields["visibility"].initial = BlogPost.VISIBILITY_PUBLIC
            if "category" in form.base_fields:
                form.base_fields["category"].initial = BlogPost.CATEGORY_STORY
        return form

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.visibility = BlogPost.VISIBILITY_PUBLIC
            if obj.category == BlogPost.CATEGORY_JOURNAL:
                obj.category = BlogPost.CATEGORY_STORY
        super().save_model(request, obj, form, change)
