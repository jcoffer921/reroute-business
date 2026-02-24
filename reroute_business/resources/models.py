# resources/models.py
from django.db import models
from django.contrib.postgres.indexes import GistIndex
from django.conf import settings
from django.utils.text import slugify

if settings.USE_GIS:
    from django.contrib.gis.db import models as gis_models


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


class Module(models.Model):
    """
    Module represents a structured learning video with an associated quiz.
    The model replaces the prior ResourceModule concept and powers the new
    AJAX quiz endpoints.
    """

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

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    video_url = models.CharField(max_length=500, blank=True, null=True)
    embed_html = models.TextField(blank=True, null=True)
    internal_content = models.TextField(blank=True, null=True)
    quiz_data = models.JSONField(blank=True, null=True)
    key_takeaways = models.JSONField(blank=True, default=list)
    poster_image = models.ImageField(upload_to="modules/posters/", blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Learning Module"
        verbose_name_plural = "Learning Modules"

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    def key_takeaways_list(self):
        """
        Normalize key takeaways to a list of trimmed strings regardless
        of whether the field stores JSON, a newline-delimited string, or
        is left blank.
        """
        data = self.key_takeaways
        if isinstance(data, str):
            items = [line.strip() for line in data.splitlines()]
            return [item for item in items if item]
        if isinstance(data, (list, tuple)):
            formatted = []
            for item in data:
                text = str(item).strip()
                if text:
                    formatted.append(text)
            return formatted
        return []


class QuizQuestion(models.Model):
    QTYPE_MULTIPLE_CHOICE = "mc"
    QTYPE_OPEN = "open"
    QTYPE_CHOICES = [
        (QTYPE_MULTIPLE_CHOICE, "Multiple Choice"),
        (QTYPE_OPEN, "Open Ended"),
    ]

    module = models.ForeignKey(Module, related_name="questions", on_delete=models.CASCADE)
    prompt = models.TextField()
    order = models.PositiveIntegerField(default=1)
    qtype = models.CharField(max_length=10, choices=QTYPE_CHOICES, default=QTYPE_MULTIPLE_CHOICE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.module.title}: Q{self.order}"


class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, related_name="answers", on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.question_id} - {self.text[:40]}"


class ModuleQuizScore(models.Model):
    module = models.ForeignKey(Module, related_name="scores", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="module_quiz_scores",
        on_delete=models.CASCADE,
    )
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("module", "user"),
                name="unique_user_module_score",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.module} ({self.score}/{self.total_questions})"


class ModuleQuizOpenResponse(models.Model):
    module = models.ForeignKey(Module, related_name="open_responses", on_delete=models.CASCADE)
    question = models.ForeignKey(QuizQuestion, related_name="open_responses", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="module_quiz_open_responses",
        on_delete=models.CASCADE,
    )
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("module", "question", "user"),
                name="unique_open_response",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.question_id}"


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


class Feature(models.Model):
    slug = models.SlugField(unique=True)
    label = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["label"]

    def save(self, *args, **kwargs):
        if not self.slug and self.label:
            self.slug = slugify(self.label)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label


class ResourceOrganization(models.Model):
    CATEGORY_HOUSING = "housing"
    CATEGORY_FOOD = "food"
    CATEGORY_ID_DOCUMENTS = "id_documents"
    CATEGORY_FINANCIAL_ASSISTANCE = "financial_assistance"
    CATEGORY_BENEFITS = "benefits"
    CATEGORY_CHILDCARE = "childcare"

    CATEGORY_HEALTHCARE = "healthcare"
    CATEGORY_MENTAL_HEALTH = "mental_health"
    CATEGORY_SUBSTANCE_USE = "substance_use"
    CATEGORY_WELLNESS = "wellness"

    CATEGORY_LEGAL = "legal"
    CATEGORY_REENTRY_ORGS = "reentry_orgs"
    CATEGORY_CASE_MANAGEMENT = "case_management"
    CATEGORY_MULTI_SERVICE = "multi_service"
    CATEGORY_GOVT_AGENCIES = "govt_agencies"

    CATEGORY_EDUCATION = "education"
    CATEGORY_CAREER_SERVICES = "career_services"
    CATEGORY_JOB_TRAINING = "job_training"
    CATEGORY_WORKFORCE_DEV = "workforce_dev"

    CATEGORY_OTHER = "other"

    CATEGORY_CHOICES = [
        (CATEGORY_HOUSING, "Housing"),
        (CATEGORY_FOOD, "Food"),
        (CATEGORY_ID_DOCUMENTS, "ID/Documents"),
        (CATEGORY_FINANCIAL_ASSISTANCE, "Financial Assistance"),
        (CATEGORY_BENEFITS, "Benefits"),
        (CATEGORY_CHILDCARE, "Childcare"),

        (CATEGORY_HEALTHCARE, "Healthcare (Medical)"),
        (CATEGORY_MENTAL_HEALTH, "Mental Health"),
        (CATEGORY_SUBSTANCE_USE, "Substance Use Treatment"),
        (CATEGORY_WELLNESS, "Health & Wellness"),

        (CATEGORY_LEGAL, "Legal Aid"),
        (CATEGORY_REENTRY_ORGS, "Reentry Organizations"),
        (CATEGORY_CASE_MANAGEMENT, "Case Management / Navigation"),
        (CATEGORY_MULTI_SERVICE, "Multi-Service Agency"),
        (CATEGORY_GOVT_AGENCIES, "Government Agencies"),

        (CATEGORY_EDUCATION, "Education & Literacy"),
        (CATEGORY_CAREER_SERVICES, "Career Services"),
        (CATEGORY_JOB_TRAINING, "Job Training"),
        (CATEGORY_WORKFORCE_DEV, "Workforce Development"),

        (CATEGORY_OTHER, "Other"),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    legacy_features = models.JSONField(default=list, blank=True)
    features = models.ManyToManyField(
        Feature,
        blank=True,
        related_name="resources",
    )
    address_line = models.CharField(max_length=255)
    neighborhood = models.CharField(max_length=255, blank=True)
    transit_line = models.CharField(max_length=255, blank=True)
    zip_code = models.CharField(max_length=5, blank=True)
    hours = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    phone_href = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    overview = models.TextField(blank=True)
    what_to_expect = models.TextField(blank=True)
    who_can_use_this = models.TextField(blank=True)
    what_to_bring = models.JSONField(blank=True, default=list)
    how_to_apply = models.TextField(blank=True)
    getting_there = models.TextField(blank=True)
    languages_supported = models.JSONField(blank=True, default=list)
    cultural_competency = models.JSONField(blank=True, default=list)
    childcare_support = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ("-is_verified", "name")
        indexes = [GistIndex(fields=["geo_point"])] if settings.USE_GIS else []
