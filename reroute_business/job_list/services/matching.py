from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import F, Q

from reroute_business.job_list.models import Job


def _has_is_remote_field() -> bool:
    return any(f.name == "is_remote" for f in Job._meta.get_fields())


def get_nearby_jobs(user_profile, miles=25):
    if not getattr(user_profile, "geo_point", None):
        return Job.objects.none()

    base_qs = Job.objects.filter(is_active=True).annotate(
        distance=Distance("geo_point", user_profile.geo_point)
    )
    has_remote = _has_is_remote_field()

    nearby_q = Q(geo_point__isnull=False, distance__lte=D(mi=miles))
    if has_remote:
        nearby_q |= Q(is_remote=True)

    return (
        base_qs
        .filter(nearby_q)
        .order_by(F("distance").asc(nulls_last=True), "-created_at")
    )
