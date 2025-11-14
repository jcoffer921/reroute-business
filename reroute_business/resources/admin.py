from django.contrib import admin
from .models import (
    Module,
    QuizQuestion,
    QuizAnswer,
    ModuleQuizScore,
    Lesson,
    LessonQuestion,
    LessonChoice,
    LessonAttempt,
    LessonProgress,
)
from .templatetags.resources_extras import youtube_embed_url


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    show_change_link = True


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    """
    Manage learning modules along with their quiz questions and answers.
    """

    list_display = ("title", "category", "video_url", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "description", "video_url")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("title", "description", "category", "key_takeaways")}),
        ("Media", {"fields": ("video_url", "embed_html", "poster_image")}),
        ("Content", {"fields": ("internal_content",)}),
    )
    inlines = [QuizQuestionInline]

    def save_model(self, request, obj, form, change):
        if obj.video_url:
            try:
                obj.video_url = youtube_embed_url(obj.video_url).strip()
            except Exception:
                pass
        super().save_model(request, obj, form, change)


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("module", "order", "qtype", "prompt")
    list_filter = ("module", "qtype")
    search_fields = ("prompt", "module__title")
    ordering = ("module", "order")
    inlines = [QuizAnswerInline]

    def get_inlines(self, request, obj=None):
        if obj and obj.qtype == QuizQuestion.QTYPE_OPEN:
            return []
        return [QuizAnswerInline]


@admin.register(ModuleQuizScore)
class ModuleQuizScoreAdmin(admin.ModelAdmin):
    list_display = ("module", "user", "score", "total_questions", "updated_at")
    list_filter = ("module",)
    search_fields = ("module__title", "user__username")
    ordering = ("-updated_at",)


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
