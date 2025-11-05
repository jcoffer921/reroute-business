from django.db import models
from django.contrib.auth.models import User
from urllib.parse import urlparse, parse_qs


class YouTubeVideo(models.Model):
    title = models.CharField(max_length=200)
    video_url = models.URLField(
        help_text=(
            "Paste a YouTube URL, e.g., https://www.youtube.com/watch?v=VIDEO_ID or https://youtu.be/VIDEO_ID"
        )
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title

    def embed_url(self) -> str:
        """Return an embeddable YouTube URL for this video."""
        val = (self.video_url or "").strip()
        if not val:
            return ""

        # Already an embed URL
        if "youtube.com/embed/" in val or "youtube-nocookie.com/embed/" in val:
            return val

        try:
            u = urlparse(val)
        except Exception:
            return val

        host = (u.netloc or "").lower()
        path = u.path or ""
        qs = parse_qs(u.query or "")

        def _append_enablejsapi(url: str) -> str:
            try:
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                u = urlparse(url)
                q = parse_qs(u.query)
                if "enablejsapi" not in q:
                    q["enablejsapi"] = ["1"]
                new_q = urlencode({k: v[-1] if isinstance(v, list) else v for k, v in q.items()})
                return urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))
            except Exception:
                return url

        # Helper to prefer nocookie embeds
        def _nocookie(url: str) -> str:
            try:
                from urllib.parse import urlparse, urlunparse
                u = urlparse(url)
                host = u.netloc.replace('www.youtube.com', 'www.youtube-nocookie.com').replace('youtube.com', 'youtube-nocookie.com')
                return urlunparse((u.scheme, host, u.path, u.params, u.query, u.fragment))
            except Exception:
                return url

        # youtu.be short links
        if host.endswith("youtu.be"):
            vid = path.lstrip("/").split("/")[0]
            return _append_enablejsapi(f"https://www.youtube-nocookie.com/embed/{vid}") if vid else val

        # youtube watch links
        if host.endswith("youtube.com") or host.endswith("m.youtube.com") or host.endswith("www.youtube.com"):
            if path.startswith("/watch"):
                vid = (qs.get("v") or [""])[0]
                return _append_enablejsapi(f"https://www.youtube-nocookie.com/embed/{vid}") if vid else val
            # shorts
            if "/shorts/" in path:
                parts = [p for p in path.split("/") if p]
                try:
                    i = parts.index("shorts")
                    vid = parts[i + 1]
                    return _append_enablejsapi(f"https://www.youtube-nocookie.com/embed/{vid}") if vid else val
                except Exception:
                    pass

        return val


