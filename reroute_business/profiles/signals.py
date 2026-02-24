# ---------------------------------
# Signals: ensure profile existence
# ---------------------------------
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from reroute_business.profiles.models import UserProfile, Subscription
from reroute_business.job_list.models import Job
from reroute_business.job_list.utils.location import zip_to_point
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
        from reroute_business.core.utils.analytics import track_event
        event_type = 'profile_created' if created else 'profile_updated'
        track_event(
            event_type=event_type,
            user=getattr(instance, 'user', None),
            metadata={'profile_id': instance.pk},
        )
    except Exception:
        # Never block on analytics
        pass


@receiver(pre_save, sender=UserProfile)
def assign_user_geo(sender, instance: UserProfile, **kwargs):
    if not settings.USE_GIS:
        return

    zip_code = (instance.zip_code or "").strip()
    if not zip_code:
        return

    if not instance.pk:
        if not instance.geo_point:
            instance.geo_point = zip_to_point(zip_code)
        return

    previous = UserProfile.objects.filter(pk=instance.pk).only("zip_code", "geo_point").first()
    zip_changed = bool(previous and (previous.zip_code or "") != zip_code)
    if not instance.geo_point or zip_changed:
        instance.geo_point = zip_to_point(zip_code)


@receiver(pre_save, sender=Job)
def assign_job_geo(sender, instance: Job, **kwargs):
    if not settings.USE_GIS:
        return

    zip_code = (instance.zip_code or "").strip()
    if not zip_code:
        return

    if not instance.pk:
        if not instance.geo_point:
            instance.geo_point = zip_to_point(zip_code)
        return

    previous = Job.objects.filter(pk=instance.pk).only("zip_code", "geo_point").first()
    zip_changed = bool(previous and (previous.zip_code or "") != zip_code)
    if not instance.geo_point or zip_changed:
        instance.geo_point = zip_to_point(zip_code)


@login_required
def remove_profile_picture(request):
    """Legacy alias that removes picture then redirects to public profile."""
    profile = request.user.profile
    if profile.profile_picture:
        profile.profile_picture.delete(save=True)
    return redirect('public_profile', username=request.user.username)
