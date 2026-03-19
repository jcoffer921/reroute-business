from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from .models import (
    Feature,
    ResourceOrganization,
    Module,
    ModuleAttempt,
    ModuleProgress,
    QuizQuestion,
    QuizAnswer,
    ModuleQuizScore,
    ModuleQuizOpenResponse,
    Lesson,
    LessonQuestion,
    LessonChoice,
    LessonAttempt,
    LessonProgress,
    ModuleResponse,
)
from .templatetags.resources_extras import youtube_embed_url


class QuizAnswerInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if not getattr(self.instance, "pk", None):
            return
        if getattr(self.instance, "qtype", None) == QuizQuestion.QTYPE_OPEN:
            if any(
                form.cleaned_data and not form.cleaned_data.get("DELETE", False)
                for form in self.forms
            ):
                raise ValidationError("Open-ended questions cannot have answer choices.")
            return
        correct_count = 0
        active_forms = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE", False):
                continue
            active_forms += 1
            if form.cleaned_data.get("is_correct"):
                correct_count += 1
        if active_forms and correct_count != 1:
            raise ValidationError("Multiple choice questions must have exactly one correct answer.")


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0
    formset = QuizAnswerInlineFormSet


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    show_change_link = True


class LessonChoiceInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if not getattr(self.instance, "pk", None):
            return
        if getattr(self.instance, "qtype", None) == LessonQuestion.TYPE_OPEN_ENDED:
            if any(
                form.cleaned_data and not form.cleaned_data.get("DELETE", False)
                for form in self.forms
            ):
                raise ValidationError("Open-ended lesson questions cannot have choices.")
            return
        correct_count = 0
        active_forms = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE", False):
                continue
            active_forms += 1
            if form.cleaned_data.get("is_correct"):
                correct_count += 1
        if active_forms and correct_count != 1:
            raise ValidationError("Multiple choice lesson questions must have exactly one correct choice.")


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    search_fields = ("label", "slug")
    list_display = ("label", "slug", "is_active")
    list_filter = ("is_active",)


@admin.register(ResourceOrganization)
class ResourceOrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "zip_code", "phone", "is_verified", "is_active", "updated_at")
    list_filter = ("is_verified", "is_active", "category")
    search_fields = ("name", "slug", "neighborhood", "zip_code", "category", "features__label", "features__slug")
    ordering = ("-is_verified", "name")
    filter_horizontal = ("features", "additional_locations")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    """
    Manage learning modules along with their quiz questions and answers.
    """

    list_display = ("title", "category", "gallery_category", "duration_minutes", "quiz_lesson_count", "video_url", "created_at")
    list_filter = ("category", "gallery_category")
    search_fields = ("title", "description", "video_url")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("title", "description", "category", "gallery_category", "duration_minutes", "quiz_lesson_count", "key_takeaways")}),
        ("Media", {"fields": ("video_url", "embed_html", "poster_image")}),
        ("Content", {"fields": ("internal_content",)}),
    )
    inlines = [QuizQuestionInline]

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        field = super().formfield_for_choice_field(db_field, request, **kwargs)
        if db_field.name == "gallery_category":
            field.help_text = "Shows this module under Browse by Category on the gallery page."
        return field

    def save_model(self, request, obj, form, change):
        if obj.video_url:
            try:
                obj.video_url = youtube_embed_url(obj.video_url).strip()
            except Exception:
                pass
        super().save_model(request, obj, form, change)


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("module", "order", "qtype", "prompt", "has_explanation")
    list_filter = ("module", "qtype")
    search_fields = ("prompt", "module__title")
    ordering = ("module", "order")
    inlines = [QuizAnswerInline]
    fields = ("module", "order", "qtype", "prompt", "explanation")

    def get_inlines(self, request, obj=None):
        if obj and obj.qtype == QuizQuestion.QTYPE_OPEN:
            return []
        return [QuizAnswerInline]

    @admin.display(boolean=True, description="Explanation")
    def has_explanation(self, obj):
        return bool((obj.explanation or "").strip())


@admin.register(ModuleQuizScore)
class ModuleQuizScoreAdmin(admin.ModelAdmin):
    list_display = ("module", "user", "score", "total_questions", "updated_at")
    list_filter = ("module",)
    search_fields = ("module__title", "user__username")
    ordering = ("-updated_at",)


@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ("module", "user", "session_key", "last_question_order", "score_percent", "completed_at", "updated_at")
    list_filter = ("module",)
    search_fields = ("module__title", "user__username", "session_key")
    ordering = ("-updated_at",)


@admin.register(ModuleAttempt)
class ModuleAttemptAdmin(admin.ModelAdmin):
    list_display = ("module", "user", "session_key", "score", "total_questions", "submitted_at")
    list_filter = ("module",)
    search_fields = ("module__title", "user__username", "session_key")
    ordering = ("-submitted_at",)


@admin.register(ModuleResponse)
class ModuleResponseAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "question_identifier", "selected_answer", "is_correct", "created_at")
    list_filter = ("attempt__module", "is_correct")
    search_fields = ("attempt__module__title", "question__prompt", "question_identifier", "text_answer")
    ordering = ("attempt", "id")


@admin.register(ModuleQuizOpenResponse)
class ModuleQuizOpenResponseAdmin(admin.ModelAdmin):
    list_display = ("module", "question", "user", "updated_at")
    list_filter = ("module", "question")
    search_fields = ("module__title", "question__prompt", "user__username", "response_text")
    ordering = ("-updated_at",)


class LessonChoiceInline(admin.TabularInline):
    model = LessonChoice
    extra = 0
    formset = LessonChoiceInlineFormSet


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
    list_display = ("lesson", "order", "timestamp_seconds", "qtype", "is_required", "is_scored", "active", "has_explanation")
    list_filter = ("qtype", "is_required", "is_scored", "active")
    search_fields = ("prompt",)
    inlines = [LessonChoiceInline]
    fields = ("lesson", "order", "timestamp_seconds", "prompt", "explanation", "qtype", "is_required", "is_scored", "active")

    @admin.display(boolean=True, description="Explanation")
    def has_explanation(self, obj):
        return bool((obj.explanation or "").strip())


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
