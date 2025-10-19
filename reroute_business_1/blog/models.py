from django.db import models
from django.utils.text import slugify


# Define reusable blog categories
BLOG_CATEGORIES = [
    ('tips', 'Tips'),
    ('motivation', 'Motivation'),
    ('news', 'Announcements'),
    ('success', 'Success Stories'),
    ('legal', 'Legal Help'),
    ('tech', 'Tech'),
    ('other', 'Other'),
]

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()
    category = models.CharField(max_length=100, default='general')
    image = models.ImageField(upload_to='blog_thumbs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
