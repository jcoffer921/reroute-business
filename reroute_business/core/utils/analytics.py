"""
Reusable analytics tracker for lightweight, safe logging.

Usage:
    from core.utils.analytics import track_event
    track_event(request=request, event_type='page_view')

This helper MUST NOT raise; failures are swallowed (logged at debug level).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.http import HttpRequest
from django.utils.timezone import now

try:
    from reroute_business.core.models import AnalyticsEvent
except Exception:  # during migrations or first deploy
    AnalyticsEvent = None  # type: ignore

logger = logging.getLogger("analytics")


def _get_client_ip(request: HttpRequest) -> str:
    # Common proxy/header patterns; fall back to REMOTE_ADDR
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR") or ""
    if x_forwarded_for:
        # may contain multiple IPs; take the first
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def track_event(
    *,
    event_type: str,
    user=None,
    path: str | None = None,
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[HttpRequest] = None,
) -> Optional[AnalyticsEvent]:
    """
    Best-effort analytics event logger. Never raises.
    Priority for `user` and `path`: explicit args > derived from request.
    Adds IP and user-agent to metadata when request is provided.
    """
    # Do nothing if the model isn't available yet (e.g., before migration)
    if AnalyticsEvent is None:
        return None

    try:
        u = user
        p = path
        meta: Dict[str, Any] = {}
        if metadata:
            meta.update(metadata)

        if request is not None:
            try:
                if u is None and getattr(request, "user", None) and request.user.is_authenticated:
                    u = request.user
            except Exception:
                pass
            p = p or getattr(request, "path", None) or ""
            # add low-cardinality request context
            try:
                meta.setdefault("ip", _get_client_ip(request))
                meta.setdefault("ua", request.META.get("HTTP_USER_AGENT", ""))
                meta.setdefault("referer", request.META.get("HTTP_REFERER", ""))
            except Exception:
                pass

        evt = AnalyticsEvent.objects.create(
            user=u if getattr(u, "is_authenticated", False) else None,
            event_type=event_type,
            path=p or "",
            metadata=meta or None,
        )
        return evt
    except Exception as exc:
        # Swallow errors to avoid breaking user flow
        logger.debug("track_event failed: %s", exc)
        return None
