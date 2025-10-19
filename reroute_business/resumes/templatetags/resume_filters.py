import os
import re
from django import template

register = template.Library()

@register.filter
def filename(value):
    """Return a basename for FileField or plain string paths."""
    try:
        name = getattr(value, "name", value)
        return os.path.basename(str(name))
    except Exception:
        return ""

_MONTHS = {
    "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "may": "May", "jun": "Jun",
    "jul": "Jul", "aug": "Aug", "sep": "Sep", "sept": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec",
}

@register.filter
def normalize_dates(s: str) -> str:
    if not s:
        return ""
    txt = str(s)

    # Normalize months at word boundaries (aug -> Aug, Sept -> Sep, etc.)
    def repl(m):
        key = m.group(0).lower()
        return _MONTHS.get(key, m.group(0).title())

    txt = re.sub(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b', repl, txt, flags=re.I)

    # Normalize "present"
    txt = re.sub(r'\bpresent\b', 'Present', txt, flags=re.I)

    # Collapse weird spaces around dashes (en/em/simple hyphen)
    txt = re.sub(r'\s*[\-\u2013\u2014]+\s*', ' - ', txt)

    # Remove duplicated parenthetical date groups e.g. "(Nov 2022) (Nov 2022)"
    txt = re.sub(r'\(([^)]+)\)\s*\(\1\)', r'(\1)', txt, flags=re.I)

    # Deduplicate repeated Month Year tokens: "Nov 2022 Nov 2022" -> "Nov 2022"
    txt = re.sub(
        r'\b((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{4})\b(\s+\1\b)+',
        r'\1',
        txt,
        flags=re.I,
    )

    # Deduplicate repeated standalone years: "2022 2022" -> "2022"
    txt = re.sub(r'\b((19|20)\d{2})\b(\s+\1\b)+', r'\1', txt)

    return txt.strip()


@register.filter
def not_blank(value) -> bool:
    """True if value has non-whitespace content."""
    try:
        return bool(str(value or '').strip())
    except Exception:
        return False


@register.filter
def strip_bullet(value: str) -> str:
    """
    Remove leading bullet-like markers (•, -, *, en/em dash) and surrounding spaces.
    Helps avoid double bullets when users paste lines starting with a bullet.
    """
    try:
        import re
        s = str(value or '')
        # Remove repeated bullet/dash/star markers at the line start
        return re.sub(r"^\s*[\u2022\-\*\u2013\u2014]+\s*", "", s)
    except Exception:
        return value
