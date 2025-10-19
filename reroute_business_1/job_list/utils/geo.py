# job_list/utils/geo.py
# PURPOSE:
#   ZIP-to-ZIP distance checks that are reliable in production.
#   - Uses an offline ZIP database first (pgeocode) → no network, fast.
#   - Falls back to geopy/Nominatim (with user_agent + timeout) if needed.
#   - Caches lookups so repeated checks don't hammer anything.
#
# USAGE:
#   from job_list.utils.geo import is_within_radius
#   is_within_radius("19104", "19107", 25) -> True/False
#
# WHY THIS WAY:
#   Relying only on Nominatim is fragile (rate limits, timeouts).
#   pgeocode is offline and good for ZIP centroids in the US.

from __future__ import annotations

from functools import lru_cache
from math import radians, sin, cos, asin, sqrt
from typing import Optional, Tuple

# --- Optional online fallback (installed via requirements) ---
try:
    from geopy.geocoders import Nominatim
except Exception:  # geopy not installed or import fails
    Nominatim = None  # type: ignore


def _is_valid_us_zip(z: str) -> bool:
    """Basic guard so we don't call geocoders with junk."""
    z = (z or "").strip()
    return len(z) == 5 and z.isdigit()


@lru_cache(maxsize=10_000)
def zip_to_latlon(zip_code: str) -> Optional[Tuple[float, float]]:
    """
    Return (lat, lon) for a US ZIP centroid, or None if unknown.

    Resolution order:
      1) pgeocode (offline)
      2) geopy/Nominatim (network) with a friendly user_agent + short timeout
    """
    if not _is_valid_us_zip(zip_code):
        return None

    # 1) Offline database: pgeocode (preferred)
    try:
        import pgeocode  # lightweight, no OS deps
        nomi = pgeocode.Nominatim("us")
        row = nomi.query_postal_code(zip_code)
        # row.latitude/longitude may be NaN; check with simple equality test
        if row is not None and row.latitude == row.latitude and row.longitude == row.longitude:
            return float(row.latitude), float(row.longitude)
    except Exception:
        # pgeocode not installed or failed; fall through to geopy
        pass

    # 2) Online fallback: geopy/Nominatim (only if library is present)
    if Nominatim is not None:
        try:
            geolocator = Nominatim(user_agent="reroute-jobs/1.0 (contact: support@reroutejobs.com)", timeout=3)
            # Nominatim supports structured queries; use 'country' or 'country_codes'
            loc = geolocator.geocode({"postalcode": zip_code, "country": "US"},
                                     addressdetails=False, exactly_one=True)
            if loc:
                return float(loc.latitude), float(loc.longitude)
        except Exception:
            # network/HTTP/timeout or rate limit -> give up gracefully
            return None

    return None


def _haversine_miles(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """
    Great-circle distance between two (lat, lon) points in MILES.
    Using haversine avoids depending on geopy.distance for runtime portability.
    """
    (lat1, lon1), (lat2, lon2) = a, b
    # Convert degrees → radians
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = (lat2 - lat1), (lon2 - lon1)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 3958.7613 * 2 * asin(min(1.0, sqrt(h)))  # 3958.7613 = Earth radius in miles


def is_within_radius(zip1: str, zip2: str, miles: int | float = 25) -> bool:
    """
    Boolean check: are the two ZIP centroids within `miles` miles?
    Returns False if either ZIP can't be resolved (keeps matching resilient).
    """
    a = zip_to_latlon(zip1)
    b = zip_to_latlon(zip2)
    if not a or not b:
        return False
    return _haversine_miles(a, b) <= float(miles)
