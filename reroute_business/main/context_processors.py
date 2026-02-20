# main/context_processors.py
# ------------------------------------------------------------
# Robust role detection that works with:
# - Group name 'Employer' OR 'Employers'
# - UserProfile fields (account_type or is_employer) if present
# - Session hint (set by a special employer login route, optional)
# - Falls back cleanly without crashing if any piece is missing
# ------------------------------------------------------------
from django.urls import reverse
from django.conf import settings

LANGUAGE_SESSION_KEY = "django_language"

def _is_employer_user(user, request=None):
    """
    Centralized 'is employer?' logic.
    We check multiple signals to future-proof the app:
      1) Django Groups: 'Employer' or 'Employers'
      2) Optional profile fields: user.userprofile.account_type / is_employer
      3) Optional session hint: request.session['force_employer'] == True
    """
    # --- Must be authenticated
    if not getattr(user, "is_authenticated", False):
        return False

    # --- 1) Groups (both singular/plural supported)
    try:
        group_names = set(user.groups.values_list("name", flat=True))
        if "Employer" in group_names or "Employers" in group_names:
            return True
    except Exception:
        pass

    # --- 2) Profile (support common attribute names)
    try:
        profile = getattr(user, "userprofile", None) or getattr(user, "profile", None)
        if profile:
            # a) account_type string (e.g., 'employer')
            acct_type = getattr(profile, "account_type", None)
            if acct_type and str(acct_type).strip().lower() in {"employer", "employers"}:
                return True
            # b) explicit boolean flag
            if getattr(profile, "is_employer", False):
                return True
    except Exception:
        pass

    # --- 3) Session hint (optional: set in your employer-login view)
    try:
        if request is not None and request.session.get("force_employer") is True:
            return True
    except Exception:
        pass

    return False


def role_flags(request):
    user = getattr(request, "user", None)
    is_auth = bool(getattr(user, "is_authenticated", False))
    is_employer = _is_employer_user(user, request) if is_auth else False

    # Compute a canonical dashboard URL
    if is_auth:
        try:
            dest = "employer_dashboard" if is_employer else "dashboard:user"
            dashboard_url = reverse(dest)
        except Exception:
            # Fallback to paths if names differ locally
            dashboard_url = "/employer/dashboard/" if is_employer else "/dashboard/"
    else:
        dashboard_url = reverse("login")

    # Canonical profile settings URL (private editor)
    if is_auth:
        if is_employer:
            try:
                profile_url = reverse("dashboard:employer_company_profile")
            except Exception:
                profile_url = "/dashboard/employer/company-profile/"
        else:
            try:
                profile_url = reverse("settings") + "?panel=profile"
            except Exception:
                profile_url = "/settings/?panel=profile"
    else:
        profile_url = reverse("login")

    # Canonical public profile URL (read-only)
    if is_auth:
        try:
            public_profile_url = reverse("profiles:public_profile", kwargs={"username": user.username})
        except Exception:
            public_profile_url = f"/profile/view/{user.username}/"
    else:
        public_profile_url = reverse("login")

    session_language = request.session.get(LANGUAGE_SESSION_KEY, "en")
    if session_language not in {"en", "es"}:
        session_language = "en"

    low_data_mode = False
    try:
        if "low_data_mode" in request.session:
            low_data_mode = bool(request.session.get("low_data_mode"))
        elif is_auth:
            profile = getattr(user, "profile", None) or getattr(user, "userprofile", None)
            low_data_mode = bool(getattr(profile, "low_data_mode", False)) if profile else False
            request.session["low_data_mode"] = low_data_mode
    except Exception:
        low_data_mode = False

    return {
        "IS_EMPLOYER": is_employer,
        "DASHBOARD_URL": dashboard_url,
        "PROFILE_URL": profile_url,
        "PUBLIC_PROFILE_URL": public_profile_url,
        "LOW_DATA_MODE": low_data_mode,
        "SITE_LANGUAGE": session_language,
        "COMPANY_LEGAL_NAME": getattr(settings, 'COMPANY_LEGAL_NAME', 'ReRoute Jobs, LLC'),
    }


def unread_notifications(request):
    """Expose unread in-app notification count for navbar badges.
    Counts only user-scoped unread notifications (excludes broadcasts).
    """
    count = 0
    user = getattr(request, 'user', None)
    try:
        if getattr(user, 'is_authenticated', False):
            from reroute_business.dashboard.models import Notification
            count = Notification.objects.filter(user=user, is_read=False).count()
    except Exception:
        count = 0
    return {"UNREAD_NOTIFICATIONS": count}
