from django import template
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import re

register = template.Library()


@register.filter
def youtube_embed_url(value: str) -> str:
    """
    Convert common YouTube URL formats into an embeddable URL.
    Supported inputs:
    - https://www.youtube.com/watch?v=VIDEO[&t=..&si=..] → https://www.youtube.com/embed/VIDEO
    - https://youtu.be/VIDEO[?t=..&si=..] → https://www.youtube.com/embed/VIDEO
    - https://www.youtube.com/shorts/VIDEO → https://www.youtube.com/embed/VIDEO
    - Playlist links with only list=... → https://www.youtube.com/embed/videoseries?list=...
    - Bare IDs (bBkWA7sBOEg) → https://www.youtube.com/embed/VIDEO
    - Already-embed URLs are returned unchanged
    """
    if not value:
        return ""

    val = str(value).strip()

    # If an entire <iframe ...> tag was pasted, extract its src URL
    if "<iframe" in val:
        m = re.search(r"src=\"([^\"]+)\"", val)
        if m:
            val = m.group(1)

    def _append_enablejsapi(url: str) -> str:
        try:
            u = urlparse(url)
            q = parse_qs(u.query)
            if "enablejsapi" not in q:
                q["enablejsapi"] = ["1"]
            new_q = urlencode({k: v[-1] if isinstance(v, list) else v for k, v in q.items()})
            return urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))
        except Exception:
            return url

    # Already an embed URL
    if "youtube.com/embed/" in val or "youtube-nocookie.com/embed/" in val:
        return _append_enablejsapi(val)

    # Bare video id (letters, numbers, -, _)
    if "://" not in val and all(c.isalnum() or c in "-_" for c in val) and 8 <= len(val) <= 64:
        return _append_enablejsapi(f"https://www.youtube.com/embed/{val}")

    try:
        u = urlparse(val)
    except Exception:
        return val

    host = (u.netloc or "").lower()
    path = u.path or ""
    qs = parse_qs(u.query or "")

    def _embed_for_video(video_id: str) -> str:
        # Prefer youtube-nocookie to avoid blockers/cookies; keep API enabled
        return _append_enablejsapi(f"https://www.youtube-nocookie.com/embed/{video_id}")

    # youtu.be short links
    if host.endswith("youtu.be"):
        vid = path.lstrip("/").split("/")[0]
        if vid:
            return _embed_for_video(vid)
        return val

    # youtube.com watch links
    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com") or host.endswith("m.youtube.com") or host.endswith("www.youtube.com"):
        # /watch?v=...
        if path.startswith("/watch"):
            vid = (qs.get("v") or [""])[0]
            if vid:
                return _embed_for_video(vid)
            # If no v param but playlist present, fall through to playlist handling

        # /shorts/VIDEO
        if "/shorts/" in path:
            parts = [p for p in path.split("/") if p]
            try:
                i = parts.index("shorts")
                vid = parts[i + 1]
                if vid:
                    return _embed_for_video(vid)
            except (ValueError, IndexError):
                pass

        # Playlist-only links
        playlist = (qs.get("list") or [""])[0]
        if playlist and not qs.get("v"):
            return _append_enablejsapi(f"https://www.youtube-nocookie.com/embed/videoseries?list={playlist}")

    # Fallback to original
    return val


@register.filter(name="endswith")
def endswith(value, suffix):
    """
    Safe string ``endswith`` check usable inside templates.

    Usage: ``{{ some_string|endswith:".mp4" }}``
    """
    if value is None or suffix is None:
        return False
    try:
        return str(value).lower().endswith(str(suffix).lower())
    except Exception:
        return False
