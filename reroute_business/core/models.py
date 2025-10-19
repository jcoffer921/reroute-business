# core/models.py

from django.db import models
from core.constants import RELATABLE_SKILLS
from django.contrib.auth.models import User  #


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class SuggestedSkill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class AnalyticsEvent(models.Model):
    """
    Lightweight analytics event for app insights.
    - user: optional, for logged-in actions
    - event_type: short string label (e.g., 'page_view', 'profile_created')
    - path: optional URL path for page views
    - metadata: JSON blob for IP, user_agent, or extra context
    - created_at: timestamp

    NOTE: Keep this non-blocking at call sites; use a best-effort helper.
    """

    EVENT_TYPES = (
        ("page_view", "Page View"),
        ("profile_view", "Profile View"),
        ("profile_created", "Profile Created"),
        ("profile_updated", "Profile Updated"),
        ("profile_completed", "Profile Completed"),
        ("resume_created", "Resume Created"),
        ("resume_updated", "Resume Updated"),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="analytics_events")
    event_type = models.CharField(max_length=64, db_index=True, choices=EVENT_TYPES)
    path = models.CharField(max_length=512, blank=True, help_text="Request path if applicable")
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        who = self.user.username if self.user else "anon"
        return f"{self.event_type} by {who} @ {self.created_at:%Y-%m-%d %H:%M:%S}"
