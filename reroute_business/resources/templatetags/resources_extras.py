from django import template

register = template.Library()


@register.filter
def youtube_embed_url(value: str) -> str:
    """
    Convert common YouTube URL formats into an embeddable URL.
    - https://www.youtube.com/watch?v=VIDEO → https://www.youtube.com/embed/VIDEO
    - https://youtu.be/VIDEO → https://www.youtube.com/embed/VIDEO
    - Bare IDs (bBkWA7sBOEg) → https://www.youtube.com/embed/VIDEO
    If the URL already looks like an embed URL, return as-is.
    """
    if not value:
        return ""

    val = str(value).strip()

    # Already an embed URL
    if "youtube.com/embed/" in val or "youtube-nocookie.com/embed/" in val:
        return val

    # Short links
    if "youtu.be/" in val:
        video_id = val.split("youtu.be/")[-1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}"

    # watch?v=
    if "youtube.com/watch" in val and "watch?v=" in val:
        return val.replace("watch?v=", "embed/")

    # Looks like a bare ID (letters, numbers, -, _)
    if all(c.isalnum() or c in "-_" for c in val) and len(val) >= 8:
        return f"https://www.youtube.com/embed/{val}"

    # Fallback to original
    return val

