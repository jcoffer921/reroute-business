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
