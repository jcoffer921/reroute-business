# profiles/views.py — slide-in friendly, JSON-first
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST


from .models import (
    UserProfile,
    EmployerProfile,
    Subscription,
    ProfileExperience,
    ProfileCertification,
)
from .constants import PROFILE_GRADIENT_CHOICES

# Optional integrations — guarded to avoid hard crashes if app not installed
try:
    from reroute_business.resumes.models import Resume
except Exception:
    Resume = None


def is_employer(user) -> bool:
    """
    Public helper used by other apps (e.g., main.views).
    Checks if the user belongs to the Employer group(s).
    Kept defensive so it never crashes if groups aren't set up.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    try:
        if hasattr(user, "employerprofile") and user.employerprofile:
            return True
    except Exception:
        pass
    try:
        return user.groups.filter(name__in=["Employer", "Employers"]).exists()
    except Exception:
        return False


def is_reentry_org(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    try:
        return user.groups.filter(
            name__in=["Reentry Org", "Reentry Organization", "Reentry", "ReentryOrg"]
        ).exists()
    except Exception:
        return False


# ----------------------------- Public profile ---------------------------
@login_required
def public_profile_view(request, username: str):
    allowed_gradients = {key for key, _label in PROFILE_GRADIENT_CHOICES}

    profile = get_object_or_404(
        UserProfile.objects.select_related("user").prefetch_related("skills", "languages"),
        user__username=username,
    )
    target_user = profile.user
    is_owner = request.user == target_user
    viewer_is_employer = is_employer(request.user)
    viewer_is_reentry = is_reentry_org(request.user)
    can_view = is_owner or viewer_is_employer or viewer_is_reentry
    if not can_view:
        raise Http404()
    if not is_owner and not profile.is_public:
        raise Http404()
    resume = (
        Resume.objects.filter(user=target_user)
        .prefetch_related("experiences")
        .order_by("-created_at")
        .first()
        if Resume
        else None
    )
    experiences = list(ProfileExperience.objects.filter(profile=profile))
    certs = list(ProfileCertification.objects.filter(profile=profile))
    if not experiences and resume:
        experiences = list(
            resume.experiences.all().order_by("-currently_work_here", "-end_date", "-start_date")
        )
    if not certs and resume:
        certs_raw = (resume.certifications or "").splitlines()
        certs = [
            {"title": line.strip(), "issuer": "", "year": ""}
            for line in certs_raw
            if line.strip()
        ]
    gradient_key = profile.background_gradient if profile.background_gradient in allowed_gradients else "aurora"

    display_first = (profile.firstname or target_user.first_name or "").strip()
    display_last = (profile.lastname or target_user.last_name or "").strip()
    display_name = (profile.preferred_name or f"{display_first} {display_last}".strip()).strip()
    status_label = profile.get_status_display() if profile.status else ""

    location_line = (profile.location or "").strip()
    if not location_line:
        if profile.city or profile.state:
            location_line = f"{profile.city or ''}{', ' if profile.city and profile.state else ''}{profile.state or ''}".strip(', ')
        elif profile.zip_code:
            location_line = profile.zip_code

    headline = (profile.headline or "").strip()
    if not headline and resume:
        headline = (resume.headline or resume.summary or "").strip()
    if not headline:
        headline = "Motivated candidate"

    about_text = (profile.bio or (resume.summary if resume else "") or "").strip()

    core_skills = [s for s in (profile.core_skills or []) if str(s).strip()]
    soft_skills = [s for s in (profile.soft_skills or []) if str(s).strip()]
    if not core_skills and resume:
        try:
            from reroute_business.resumes.models import ResumeSkill
            core_skills = list(
                ResumeSkill.objects.filter(resume=resume, category="technical")
                .select_related("skill")
                .values_list("skill__name", flat=True)
            )
            soft_skills = list(
                ResumeSkill.objects.filter(resume=resume, category="soft")
                .select_related("skill")
                .values_list("skill__name", flat=True)
            )
        except Exception:
            core_skills = []
            soft_skills = []
    if not core_skills and resume:
        try:
            core_skills = list(resume.skills.values_list("name", flat=True))
        except Exception:
            core_skills = []

    applications_count = 0
    interviews_count = 0
    profile_views_count = 0
    try:
        from reroute_business.job_list.models import Application
        applications_count = Application.objects.filter(applicant=target_user).count()
        interviews_count = Application.objects.filter(applicant=target_user, status="interview").count()
    except Exception:
        pass
    if is_owner:
        try:
            from reroute_business.core.models import AnalyticsEvent
            profile_views_count = AnalyticsEvent.objects.filter(
                event_type="profile_view",
                metadata__viewed_user=target_user.username,
            ).count()
        except Exception:
            profile_views_count = 0

    active_jobs = []
    if viewer_is_employer:
        try:
            from reroute_business.job_list.models import Job, JobInvitation
            active_jobs = list(Job.objects.filter(employer=request.user, is_active=True).order_by("-created_at"))
            invited = JobInvitation.objects.filter(employer=request.user, candidate=target_user).exists()
        except Exception:
            invited = False
    else:
        invited = False

    is_saved = False
    if (viewer_is_employer or viewer_is_reentry) and not is_owner:
        try:
            from reroute_business.job_list.models import SavedCandidate
            is_saved = SavedCandidate.objects.filter(saved_by=request.user, candidate=target_user).exists()
        except Exception:
            is_saved = False

    # Track a specific profile-view event (best-effort, non-blocking)
    try:
        from reroute_business.core.utils.analytics import track_event
        track_event(
            event_type="profile_view",
            user=request.user,
            path=request.path,
            metadata={"viewed_user": username},
            request=request,
        )
    except Exception:
        pass

    return render(
        request,
        "profiles/public_profile.html",
        {
            "viewed_user": target_user,
            "profile": profile,
            "experiences": experiences,
            "certifications": certs,
            "core_skills": core_skills,
            "soft_skills": soft_skills,
            "display_first": display_first,
            "display_last": display_last,
            "display_name": display_name or target_user.username,
            "headline": headline,
            "about_text": about_text,
            "location_line": location_line,
            "status_label": status_label,
            "applications_count": applications_count,
            "interviews_count": interviews_count,
            "profile_views_count": profile_views_count,
            "gradient_key": gradient_key,
            "is_owner": is_owner,
            "is_employer_view": viewer_is_employer,
            "is_reentry_view": viewer_is_reentry,
            "active_jobs": active_jobs,
            "invite_sent": invited,
            "is_saved": is_saved,
            "can_invite": bool(viewer_is_employer),
            "resume": resume,
        },
    )


# ----------------------------- Own profile ------------------------------
@login_required
def user_profile_view(request):
    """Legacy owner profile page -> redirect to Profile Settings."""
    return redirect(f"{reverse('settings')}?panel=profile")

# ----------------------------- Employer Profile -------------------------
@login_required
def employer_profile_view(request):
    """
    Employer Profile view (front-end focused)
    - Ensures the current user has an EmployerProfile row (creates a blank one if missing)
    - Renders a simple form to update employer details inside a slide-out panel
    - Avoids any changes to the employer dashboard or other flows

    Notes for non-technical partners:
    - When you click "Edit Profile", a panel slides in from the right.
    - Submitting the form saves changes and reloads this page.
    - The green Verified badge appears if verification is true; otherwise a yellow pending badge shows.
    """
    return redirect('dashboard:employer_company_profile')


def employer_public_profile_view(request, username: str):
    """
    Public, read-only employer profile page by username.
    Modern layout with hero, About, current openings (up to 3), and info grid.
    """
    user = get_object_or_404(User, username=username)
    employer_profile = get_object_or_404(EmployerProfile, user=user)

    # Pull up to 3 active jobs for this employer
    try:
        from reroute_business.job_list.models import Job
        jobs_qs = Job.objects.filter(is_active=True, employer=user).order_by('-created_at')
        total_jobs = jobs_qs.count()
        jobs = list(jobs_qs[:3])
    except Exception:
        jobs, total_jobs = [], 0

    # Build a "View All Jobs" link that filters by employer on the opportunities page
    from django.urls import reverse
    view_all_url = None
    try:
        view_all_base = reverse('opportunities')
        view_all_url = f"{view_all_base}?employer={user.username}"
    except Exception:
        pass

    return render(
        request,
        "profiles/employer_public_profile.html",
        {
            "employer_profile": employer_profile,
            "viewed_user": user,
            "jobs": jobs,
            "total_jobs": total_jobs,
            "view_all_url": view_all_url,
        },
    )


@login_required
@require_POST
def toggle_candidate_bookmark(request, username: str):
    if not (is_employer(request.user) or is_reentry_org(request.user)):
        return JsonResponse({"ok": False, "error": "Not allowed."}, status=403)

    candidate = get_object_or_404(User, username=username, is_active=True)
    if candidate == request.user:
        return JsonResponse({"ok": False, "error": "Cannot save your own profile."}, status=400)
    try:
        if hasattr(candidate, 'employerprofile') and candidate.employerprofile:
            return JsonResponse({"ok": False, "error": "Cannot save employer profiles."}, status=400)
    except Exception:
        pass

    try:
        from reroute_business.job_list.models import SavedCandidate
    except Exception:
        return JsonResponse({"ok": False, "error": "Save feature not available."}, status=501)

    existing = SavedCandidate.objects.filter(saved_by=request.user, candidate=candidate).first()
    if existing:
        existing.delete()
        return JsonResponse({"ok": True, "saved": False})

    SavedCandidate.objects.create(saved_by=request.user, candidate=candidate)
    return JsonResponse({"ok": True, "saved": True})


@login_required
@require_POST
def remove_employer_logo(request):
    """
    Remove the current employer's logo.
    Keeps the rest of the profile intact. Redirects back to employer profile.
    """
    prof, _ = EmployerProfile.objects.get_or_create(user=request.user)
    if prof.logo:
        try:
            prof.logo.delete(save=False)
        except Exception:
            # Ignore storage errors — absence is fine
            pass
        prof.logo = None
        prof.save(update_fields=["logo"])
        messages.success(request, "Company logo removed.")
    else:
        messages.info(request, "No company logo to remove.")
    return redirect('employer_profile')

# ----------------------------- Onboarding Final (example) ---------------
@login_required
def final_view(request):
    """
    Example of logging profile completion when the user lands here.
    If you already have a final step view, add the same track_event call there.
    """
    try:
        from reroute_business.core.utils.analytics import track_event
        track_event(event_type='profile_completed', request=request, metadata={"source": "profiles.final_view"})
    except Exception:
        pass

    # Optionally flash a message or update state before redirect
    return redirect(f"{reverse('settings')}?panel=profile")


# ----------------------------- Subscription Settings --------------------
@login_required
def subscription_settings(request):
    """Legacy subscription page -> redirect to Settings billing panel."""
    return redirect(f"{reverse('settings')}?panel=billing")


@login_required
@require_POST
def cancel_subscription(request):
    """
    Employers only: cancel subscription.
    - Set plan to 'Free'
    - Mark subscription inactive
    - Redirect back with success message
    """
    if not is_employer(request.user):
        messages.error(request, "You do not have access to cancel a subscription.")
        return redirect("profiles:subscription_settings")

    sub, _ = Subscription.objects.get_or_create(user=request.user)
    sub.plan_name = Subscription.PLAN_FREE
    sub.active = False
    try:
        from django.utils import timezone
        sub.expiry_date = timezone.now()
    except Exception:
        pass
    sub.save()

    messages.success(request, "Your subscription has been cancelled and reverted to Free.")
    return redirect("profiles:subscription_settings")
