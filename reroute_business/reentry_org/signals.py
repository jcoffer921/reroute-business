from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.conf import settings

from reroute_business.job_list.utils.location import zip_to_point
from reroute_business.reentry_org.models import ReentryOrganization


@receiver(pre_save, sender=ReentryOrganization)
def assign_org_geo_point(sender, instance: ReentryOrganization, **kwargs):
    if not settings.USE_GIS:
        return

    zip_code = (instance.zip_code or "").strip()
    if not zip_code:
        return

    if not instance.pk:
        if not instance.geo_point:
            instance.geo_point = zip_to_point(zip_code)
        return

    previous = ReentryOrganization.objects.filter(pk=instance.pk).only("zip_code", "geo_point").first()
    zip_changed = bool(previous and (previous.zip_code or "") != zip_code)
    if not instance.geo_point or zip_changed:
        instance.geo_point = zip_to_point(zip_code)
