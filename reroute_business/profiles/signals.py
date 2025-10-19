# ---------------------------------
# Signals: ensure profile existence
# ---------------------------------
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from profiles.models import UserProfile, Subscription
from django.contrib.auth.models import User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        # Ensure every user has a Subscription row
        Subscription.objects.get_or_create(user=instance)


@receiver(post_save, sender=UserProfile)
def track_userprofile_change(sender, instance: UserProfile, created: bool, **kwargs):
    """Log profile create/update as analytics events (non-blocking)."""
    try:
        from core.utils.analytics import track_event
        event_type = 'profile_created' if created else 'profile_updated'
        track_event(
            event_type=event_type,
            user=getattr(instance, 'user', None),
            metadata={'profile_id': instance.pk},
        )
    except Exception:
        # Never block on analytics
        pass


@login_required
def remove_profile_picture(request):
    """Legacy alias that removes picture then redirects to public profile."""
    profile = request.user.profile
    if profile.profile_picture:
        profile.profile_picture.delete(save=True)
    return redirect('public_profile', username=request.user.username)
