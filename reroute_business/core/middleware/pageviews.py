from __future__ import annotations

from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from core.utils.analytics import track_event


class PageViewMiddleware:
    """
    Lightweight page-view tracker for HTML GET requests.
    - Skips admin, static, and media paths.
    - Records event_type='page_view' with user + path + basic request metadata.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        try:
            # Only track successful HTML GETs
            if request.method != "GET":
                return response
            if response.status_code != 200:
                return response
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return response

            path = request.path or ""
            # Skip obvious noise
            if path.startswith("/admin"):
                return response
            if settings.STATIC_URL and path.startswith(settings.STATIC_URL):
                return response
            if getattr(settings, "MEDIA_URL", None) and path.startswith(settings.MEDIA_URL):
                return response
            # Skip common non-page assets
            if path in {"/favicon.ico", "/robots.txt", "/sitemap.xml"}:
                return response

            # Record best-effort page view
            track_event(event_type="page_view", request=request)
        except Exception:
            # Never block the response
            pass

        return response
