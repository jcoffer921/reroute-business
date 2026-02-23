from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class BlogPost(models.Model):
    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"

    CATEGORY_JOURNAL = "journal"
    CATEGORY_STORY = "story"
    CATEGORY_FAIR_CHANCE = "fair_chance"
    CATEGORY_TIPS = "tips"
    CATEGORY_UPDATES = "updates"
    CATEGORY_REENTRY = "reentry"

    JOURNAL_TAG_INTERVIEW = "interview"
    JOURNAL_TAG_JOB_SEARCH = "job_search"
    JOURNAL_TAG_CONFIDENCE = "confidence"
    JOURNAL_TAG_TRAINING = "training"
    JOURNAL_TAG_PERSONAL_GROWTH = "personal_growth"

    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    ]

    CATEGORY_CHOICES = [
        (CATEGORY_JOURNAL, "Journal"),
        (CATEGORY_STORY, "Story"),
        (CATEGORY_FAIR_CHANCE, "Fair-Chance Hiring"),
        (CATEGORY_TIPS, "Job Seeker Tips"),
        (CATEGORY_UPDATES, "Platform Updates"),
        (CATEGORY_REENTRY, "Reentry Orgs"),
    ]

    JOURNAL_TAG_CHOICES = [
        (JOURNAL_TAG_INTERVIEW, "Interview"),
        (JOURNAL_TAG_JOB_SEARCH, "Job Search"),
        (JOURNAL_TAG_CONFIDENCE, "Confidence"),
        (JOURNAL_TAG_TRAINING, "Training"),
        (JOURNAL_TAG_PERSONAL_GROWTH, "Personal Growth"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, null=True, blank=True)
    content = models.TextField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="blog_entries",
    )
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PRIVATE,
    )
    category = models.CharField(
        max_length=40,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_JOURNAL,
    )
    journal_tag = models.CharField(
        max_length=32,
        choices=JOURNAL_TAG_CHOICES,
        blank=True,
    )
    image = models.ImageField(upload_to="blog_thumbs/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)

    def clean(self):
        errors = {}

        if self.visibility == self.VISIBILITY_PUBLIC and not self.slug:
            errors["slug"] = "Slug is required for public content."

        if self.visibility == self.VISIBILITY_PRIVATE:
            if not self.owner:
                errors["owner"] = "Private journal entries must have an owner."
            if self.category != self.CATEGORY_JOURNAL:
                errors["category"] = "Private entries must use the Journal category."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.visibility == self.VISIBILITY_PUBLIC and not self.slug:
            base_slug = slugify(self.title)[:45] or "story"
            slug = base_slug
            index = 2
            while BlogPost.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base_slug}-{index}"
                index += 1
            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
