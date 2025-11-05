from django.contrib import admin
from .models import (
    ResourceModule,
    Lesson,
    LessonQuestion,
    LessonChoice,
    LessonAttempt,
    LessonProgress,
)
from .templatetags.resources_extras import youtube_embed_url


@admin.register(ResourceModule)
class ResourceModuleAdmin(admin.ModelAdmin):
    """
    Admin configuration to manage Learning Modules.
    - Search by title and description for quick discovery.
    - Filter by category to narrow down content.
    - Default ordering shows most recent first.
    """

    list_display = ("title", "category", "video_url", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "description", "video_url")
    ordering = ("-created_at",)
    fields = ("title", "description", "category", "video_url", "embed_html", "internal_content")

    def save_model(self, request, obj, form, change):
        # Normalize any YouTube or pasted iframe into a clean embed URL
        if obj.video_url:
            try:
                obj.video_url = youtube_embed_url(obj.video_url).strip()
            except Exception:
                # If normalization fails, keep original to avoid data loss
                pass
        super().save_model(request, obj, form, change)


class LessonChoiceInline(admin.TabularInline):
    model = LessonChoice
    extra = 0


class LessonQuestionInline(admin.TabularInline):
    model = LessonQuestion
    extra = 0


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_active", "created_at")
    search_fields = ("title", "description", "slug")
    list_filter = ("is_active",)
    inlines = [LessonQuestionInline]


@admin.register(LessonQuestion)
class LessonQuestionAdmin(admin.ModelAdmin):
    list_display = ("lesson", "order", "timestamp_seconds", "qtype", "is_required", "is_scored", "active")
    list_filter = ("qtype", "is_required", "is_scored", "active")
    search_fields = ("prompt",)
    inlines = [LessonChoiceInline]


@admin.register(LessonAttempt)
class LessonAttemptAdmin(admin.ModelAdmin):
    list_display = ("question", "user", "session_key", "is_correct", "attempt_number", "video_time", "created_at")
    list_filter = ("is_correct", "question__lesson")
    search_fields = ("session_key", "open_text")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = (
        "lesson",
        "user",
        "session_key",
        "correct_count",
        "scored_count",
        "accuracy_percent",
        "last_video_time",
        "last_answered_question_order",
        "completed_at",
        "updated_at",
    )
    list_filter = ("lesson",)
    search_fields = ("session_key",)
