from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    """Unified in‑app notification model.

    Existing, action‑driven notifications (e.g. job applications) continue to use
    the original fields `user`, `verb`, `message`, etc.

    To support admin‑authored messages and optional broadcast, we add:
    - `title`: short headline for admin messages
    - `target_group`: broadcast target for role‑based delivery
    - allow `user` to be optional so admin can create a single broadcast row

    Delivery logic in views will show a notification to a given user if:
    - `user == request.user`, OR
    - `user is null` AND `target_group` matches (or is ALL)
    """

    # Recipient of a direct notification (nullable to enable broadcasts)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        help_text="Target user for direct notifications. Leave empty for broadcasts.",
    )

    # Admin-authored headline (optional for legacy action notifications)
    title = models.CharField(max_length=200, blank=True, help_text="Short title for admin messages")

    # Body text (used by both action and admin messages)
    message = models.TextField()

    # Optional actor + verb for action-style notifications (kept for backward compat)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actor_notifications",
        help_text="User who triggered the event (for action notifications)",
    )
    verb = models.CharField(max_length=100, blank=True, help_text="Action verb (e.g., applied)")
    url = models.CharField(max_length=255, blank=True, null=True, help_text="Optional link for CTA")

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional foreign keys to correlate context (not required for schema portability)
    job = models.ForeignKey('job_list.Job', on_delete=models.SET_NULL, null=True, blank=True)
    application = models.ForeignKey('job_list.Application', on_delete=models.SET_NULL, null=True, blank=True)

    # Optional broadcast targeting (admin-authored)
    TARGET_ALL = 'ALL'
    TARGET_EMPLOYERS = 'EMPLOYERS'
    TARGET_SEEKERS = 'SEEKERS'
    TARGET_CHOICES = [
        (TARGET_ALL, 'All Users'),
        (TARGET_EMPLOYERS, 'Employers'),
        (TARGET_SEEKERS, 'Job Seekers'),
    ]
    target_group = models.CharField(
        max_length=10,
        choices=TARGET_CHOICES,
        blank=True,
        help_text="Leave blank for direct messages; choose a group to broadcast",
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        # Prefer a friendly display including title when present
        who = self.user.username if self.user_id else (self.target_group or "broadcast")
        title = self.title or self.verb or (self.message[:30] + ("…" if len(self.message) > 30 else ""))
        return f"Notification(to={who}, title={title}, read={self.is_read})"

    # Convenience alias to satisfy "recipient" terminology in admin/UI
    @property
    def recipient(self):  # read-only alias for templates/admin list_display
        return self.user




class Interview(models.Model):
    """
    Scheduled interview between an employer and a candidate for a job.
    """
    STATUS_PLANNED = 'planned'
    STATUS_RESCHEDULED = 'rescheduled'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELED = 'canceled'
    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Planned'),
        (STATUS_RESCHEDULED, 'Rescheduled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELED, 'Canceled'),
    ]

    job = models.ForeignKey('job_list.Job', on_delete=models.CASCADE, related_name='interviews')
    employer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employer_interviews')
    candidate = models.ForeignKey(User, on_delete=models.CASCADE, related_name='candidate_interviews')

    scheduled_at = models.DateTimeField(db_index=True)
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at', 'id']
        indexes = [
            models.Index(fields=['employer', 'scheduled_at']),
            models.Index(fields=['candidate', 'scheduled_at']),
            models.Index(fields=['job', 'scheduled_at']),
        ]

    def __str__(self):
        return f"Interview({self.job.title} - {self.candidate.username} at {self.scheduled_at:%Y-%m-%d %H:%M})"
