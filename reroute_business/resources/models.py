# resources/models.py
from django.db import models
from django.conf import settings


class Resource(models.Model):
    CATEGORY_CHOICES = [
        ('job', 'Job Tools'),
        ('tech', 'Tech Training'),
        ('reentry', 'Reentry Support'),
        ('video', 'How-To Video'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    link = models.URLField(blank=True)
    video_embed = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class ResourceModule(models.Model):
    """
    ResourceModule represents a structured learning resource that displays
    directly on the site (no redirects). It includes a title, short
    description, a category (with predefined choices), optional internal
    content, and an optional embed HTML (e.g., an iframe) for inline video.
    A creation timestamp supports ordering by most recent in the UI.
    """

    # Category choices for grouping modules on the page
    CATEGORY_WORKFORCE = "workforce"
    CATEGORY_DIGITAL = "digital"
    CATEGORY_REENTRY = "reentry"
    CATEGORY_LIFE = "life"

    CATEGORY_CHOICES = [
        (CATEGORY_WORKFORCE, "Workforce Readiness"),
        (CATEGORY_DIGITAL, "Digital Skills"),
        (CATEGORY_REENTRY, "Reentry Support"),
        (CATEGORY_LIFE, "Life Skills"),
    ]

    # Core module fields
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    # Optional video URL (YouTube or local static path). If present, UI
    # auto-detects the correct player (iframe vs <video>). Prefer this over
    # embed_html for new content.
    video_url = models.CharField(max_length=500, blank=True, null=True)

    # Optional embedded video HTML (iframe); used to render inline player
    embed_html = models.TextField(blank=True, null=True)

    # Optional internal rich content (future: lessons, text, steps)
    internal_content = models.TextField(blank=True, null=True)

    # Timestamp for ordering by recency in the Resources page
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Learning Module"
        verbose_name_plural = "Learning Modules"

    def __str__(self):
        # Helpful for admin listings
        return f"{self.title} ({self.get_category_display()})"


# --- Interactive Lesson Models ---

class Lesson(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    video_static_path = models.CharField(
        max_length=500,
        help_text="Static path under /static, e.g., /static/resources/videos/ResumeBasics101-improved.mp4",
    )
    youtube_video_id = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="Optional YouTube video ID (e.g., bBkWA7sBOEg) to stream via YouTube player.",
    )
    duration_seconds = models.FloatField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title


class LessonQuestion(models.Model):
    TYPE_MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    TYPE_OPEN_ENDED = "OPEN_ENDED"
    TYPE_CHOICES = [
        (TYPE_MULTIPLE_CHICE := TYPE_MULTIPLE_CHOICE, "Multiple Choice"),
        (TYPE_OPEN_ENDED, "Open Ended"),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=1)
    timestamp_seconds = models.FloatField(help_text="Time in seconds when the question should appear")
    prompt = models.TextField()
    qtype = models.CharField(max_length=32, choices=TYPE_CHOICES, default=TYPE_MULTIPLE_CHOICE)
    is_required = models.BooleanField(default=True)
    is_scored = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("order",)

    def __str__(self):
        return f"{self.lesson.title} Q{self.order}: {self.prompt[:40]}..."


class LessonChoice(models.Model):
    question = models.ForeignKey(LessonQuestion, on_delete=models.CASCADE, related_name="choices")
    label = models.CharField(max_length=5, help_text="e.g., a, b, c, d")
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("position",)

    def __str__(self):
        return f"{self.question.order}{self.label}) {self.text[:30]}"


class LessonAttempt(models.Model):
    question = models.ForeignKey(LessonQuestion, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="lesson_attempts"
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    selected_choice = models.ForeignKey(LessonChoice, null=True, blank=True, on_delete=models.SET_NULL)
    open_text = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    attempt_number = models.PositiveIntegerField(default=1)
    video_time = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class LessonProgress(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="lesson_progress"
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    correct_count = models.PositiveIntegerField(default=0)
    scored_count = models.PositiveIntegerField(default=0)
    accuracy_percent = models.PositiveIntegerField(default=0)
    last_video_time = models.FloatField(default=0)
    last_answered_question_order = models.PositiveIntegerField(default=0)
    raw_state = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self):
        who = self.user.username if self.user_id else (self.session_key or "guest")
        return f"{self.lesson.slug} progress for {who}"
