from django import template
from django.urls import reverse
from django.utils.timezone import now
import hashlib

register = template.Library()

@register.filter
def split_by_comma(value):
    """
    Accepts either a comma-separated string OR a ManyToMany queryset
    and returns a list of stripped skill names.
    """
    if not value:
        return []

    # Handle ManyToMany fields or related managers
    if hasattr(value, 'all'):
        return [str(s).strip() for s in value.all()]

    # Handle comma-separated strings
    if isinstance(value, str):
        return [s.strip() for s in value.split(',')]

    return []


@register.filter(name="initials")
def initials(user):
    """Return the user's initials from first/last name or username.
    Safe for missing fields; returns an uppercase 1–2 character string.
    """
    try:
        first = (getattr(user, 'first_name', '') or '').strip()
        last = (getattr(user, 'last_name', '') or '').strip()
        if first or last:
            return (first[:1] + last[:1]).upper()
        uname = (getattr(user, 'username', '') or '').strip()
        return uname[:2].upper()
    except Exception:
        return ""


@register.filter(name="profile_picture_url")
def profile_picture_url(user):
    """Return profile picture URL for a user if available, else empty string.
    Works with UserProfile model attached as `user.profile`.
    """
    try:
        profile = getattr(user, 'profile', None)
        if profile and getattr(profile, 'profile_picture', None) and getattr(profile.profile_picture, 'url', ''):
            return profile.profile_picture.url
    except Exception:
        pass
    return ""


@register.filter(name="employer_logo_url")
def employer_logo_url(user):
    """Return employer logo URL if EmployerProfile and logo exist; else empty string."""
    try:
        emp = getattr(user, 'employerprofile', None)
        logo = getattr(emp, 'logo', None)
        url = getattr(logo, 'url', '') if logo else ''
        return url or ""
    except Exception:
        return ""


@register.filter(name="employer_company")
def employer_company(user):
    """Return company name from EmployerProfile if present; else username."""
    try:
        emp = getattr(user, 'employerprofile', None)
        name = getattr(emp, 'company_name', '')
        if name:
            return name
        return getattr(user, 'username', '')
    except Exception:
        return getattr(user, 'username', '')


@register.filter(name="employer_public_url")
def employer_public_url(user):
    """Reverse the public employer profile URL by username. Returns path string."""
    try:
        uname = getattr(user, 'username', '')
        if not uname:
            return ''
        return reverse('employer_public_profile', kwargs={'username': uname})
    except Exception:
        return ''


@register.filter(name="file_version")
def file_version(fieldfile):
    """
    Safe cache-busting token for FieldFile-like objects.
    - Prefer .size if accessible
    - Fallback to md5(name)[:8]
    - Fallback to current epoch seconds
    Never raises; returns a string/int suitable for use in query params.
    """
    try:
        # FieldFile.size may hit storage; guard with try/except
        sz = getattr(fieldfile, 'size', None)
        if sz:
            return sz
    except Exception:
        pass
    try:
        name = getattr(fieldfile, 'name', '') or ''
        if name:
            return hashlib.md5(name.encode('utf-8')).hexdigest()[:8]
    except Exception:
        pass
    try:
        return int(now().timestamp())
    except Exception:
        return ''
