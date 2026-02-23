from django.conf import settings

from reroute_business.job_list.models import ZipCentroid
from reroute_business.job_list.utils.geo import zip_to_latlon

if settings.USE_GIS:
    from django.contrib.gis.geos import Point

def _normalize_zip(zip_code: str) -> str:
    raw = (zip_code or "").strip()
    if not raw:
        return ""
    base = raw.split("-")[0]
    return base[:5]


def ensure_zip_centroid(zip_code: str):
    if not settings.USE_GIS:
        return None
    normalized = _normalize_zip(zip_code)
    if not normalized:
        return None

    existing = ZipCentroid.objects.filter(zip_code=normalized).values_list("geo_point", flat=True).first()
    if existing:
        return existing

    latlon = zip_to_latlon(normalized)
    if not latlon:
        return None

    latitude, longitude = latlon
    point = Point(longitude, latitude, srid=4326)
    ZipCentroid.objects.update_or_create(
        zip_code=normalized,
        defaults={"geo_point": point},
    )
    return point


def zip_to_point(zip_code: str):
    normalized = _normalize_zip(zip_code)
    if not normalized:
        return None
    return ensure_zip_centroid(normalized)
