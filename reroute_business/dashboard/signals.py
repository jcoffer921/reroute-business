from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from .models import Interview, Notification


def _notify(user, title, message, url=None, job=None):
    try:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            url=url or '',
            job=job,
        )
    except Exception:
        pass


@receiver(pre_save, sender=Interview)
def interview_change_notifications(sender, instance: Interview, **kwargs):
    """
    On interview updates, notify involved parties when:
      - scheduled_at changes (reschedule)
      - status changes to canceled (cancellation)
    Creation notifications are handled in the view.
    """
    if not instance.pk:
        # New instance, let the creating view handle notifications
        return

    try:
        prev = Interview.objects.get(pk=instance.pk)
    except Interview.DoesNotExist:
        return

    job = instance.job
    employer = instance.employer
    candidate = instance.candidate

    # Detect reschedule
    try:
        if prev.scheduled_at != instance.scheduled_at:
            when = instance.scheduled_at.astimezone(timezone.get_current_timezone())
            when_str = when.strftime('%b %d, %Y %I:%M %p')
            msg_emp = f"Interview with {candidate.get_full_name() or candidate.username} for '{job.title}' was rescheduled to {when_str}."
            msg_cand = f"Your interview for '{job.title}' was rescheduled to {when_str}."
            _notify(
                employer,
                title="Interview Rescheduled",
                message=msg_emp,
                url=reverse('dashboard:employer'),
                job=job,
            )
            _notify(
                candidate,
                title="Interview Rescheduled",
                message=msg_cand,
                url=reverse('dashboard:user'),
                job=job,
            )
    except Exception:
        pass

    # Detect cancellation
    try:
        if prev.status != instance.status and instance.status == Interview.STATUS_CANCELED:
            when = prev.scheduled_at.astimezone(timezone.get_current_timezone())
            when_str = when.strftime('%b %d, %Y %I:%M %p')
            msg_emp = f"Interview with {candidate.get_full_name() or candidate.username} for '{job.title}' on {when_str} was canceled."
            msg_cand = f"Your interview for '{job.title}' on {when_str} was canceled."
            _notify(
                employer,
                title="Interview Canceled",
                message=msg_emp,
                url=reverse('dashboard:employer'),
                job=job,
            )
            _notify(
                candidate,
                title="Interview Canceled",
                message=msg_cand,
                url=reverse('dashboard:user'),
                job=job,
            )
    except Exception:
        pass

