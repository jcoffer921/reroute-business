# resources/models.py
from django.db import models


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


class LearningModule(models.Model):
    """
    LearningModule represents a structured learning resource that can be
    displayed on the public Resources page. It includes a title, short
    description, a category (with predefined choices), an optional external
    link to content (e.g., video/course/article), optional internal content,
    and an auto-populated creation timestamp for ordering by recency.
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
    external_link = models.URLField(blank=True, null=True)
    internal_content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Learning Module"
        verbose_name_plural = "Learning Modules"

    def __str__(self):
        # Helpful for admin listings
        return f"{self.title} ({self.get_category_display()})"
