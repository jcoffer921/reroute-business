# dashboard/views.py

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator



# ===== Domain imports (align to your actual apps) =====
# Jobs live in job_list; bring Job, SavedJob, Application from there for consistency.
from reroute_business.job_list.models import Job, SavedJob, Application
from reroute_business.job_list.models import ArchivedJob
from django.db.utils import ProgrammingError
from reroute_business.job_list.matching import match_jobs_for_user
from reroute_business.job_list.services.matching import get_nearby_jobs

# Profiles & resumes
from reroute_business.profiles.models import UserProfile, Language
from reroute_business.profiles.constants import PROFILE_GRADIENT_CHOICES, GENDER_CHOICES
from reroute_business.core.models import Skill
from reroute_business.core.utils.onboarding import log_onboarding_event
from reroute_business.resumes.models import Education, Experience, Resume  # your resumes app owns these
from PIL import Image, UnidentifiedImageError
from reroute_business.resources.models import Module
from reroute_business.reentry_org.models import ReentryOrganization, SavedOrganization
from reroute_business.main.models import YouTubeVideo


# =========================
# Role helpers
# =========================
def is_employer(user):
    """Return True if the user is in the Employer group."""
    return user.is_authenticated and user.groups.filter(name='Employer').exists()

def is_admin(user):
    """True if user is staff or superuser (your choice to treat both as admin)."""
    return user.is_authenticated and (user.is_superuser or user.is_staff)


# =========================
# Utilities
# =========================
def extract_resume_skills(resume):
    """
    Return a list of skill strings from a resume, regardless of storage:
    - If ManyToMany: map objects → .name (or str())
    - If TextField: split by commas
    - If nothing present: []
    """
    if not resume:
        return []

    # Case A: ManyToMany-like (has .all attr)
    if hasattr(resume, "skills") and hasattr(getattr(resume, "skills"), "all"):
        return [
            (getattr(s, "name", str(s)) or "").strip()
            for s in resume.skills.all()
            if (getattr(s, "name", str(s)) or "").strip()
        ]

    # Case B: Text field
    raw = getattr(resume, "skills", "") or ""
    return [s.strip() for s in raw.split(",") if s.strip()]


def _json_ok(payload=None, status=200):
    data = {"ok": True}
    if payload:
        data.update(payload)
    return JsonResponse(data, status=status)


def _json_err(errors, status=400):
    return JsonResponse({"ok": False, "errors": errors}, status=status)


def _reports_flags_count():
    try:
        return Job.objects.filter(is_flagged=True).count()
    except Exception:
        return 0


def _extract_youtube_id(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""

    if "youtube.com/embed/" in raw or "youtube-nocookie.com/embed/" in raw:
        return raw.rstrip("/").split("/")[-1].split("?")[0]

    try:
        parsed = urlparse(raw)
    except Exception:
        return ""

    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")
    query = parse_qs(parsed.query or "")

    if host.endswith("youtu.be"):
        return path.split("/")[0]

    if "youtube.com" in host:
        if path == "watch":
            return (query.get("v") or [""])[0]
        if path.startswith("shorts/"):
            return path.split("/", 1)[1]

    return ""


# =========================
# Router / Redirect
# =========================
@login_required
def dashboard_redirect(request):
    """
    Legacy-safe: send /dashboard/ hits to the correct destination.
    Priority: Admin > Employer > User.
    """
    if is_admin(request.user):
        return redirect('dashboard:admin')      # namespaced dashboard app
    if is_employer(request.user):
        return redirect('dashboard:employer')
    return redirect('dashboard:user')


# =========================
# User Dashboard
# =========================
@login_required
def user_dashboard(request):
    """
    Loads the user's profile, resume, applications, and suggested jobs
    (only if we can detect at least one skill).
    """
    # Ensure a profile exists to avoid template conditionals blowing up
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    early_access_mode = bool(getattr(settings, "EARLY_ACCESS_MODE", False))
    jobs_live = bool(getattr(settings, "JOBS_LIVE", False))
    early_access_message = (
        "ReRoute is in early access. Employers and reentry organizations are onboarding now. "
        "Completed profiles get priority access when jobs launch."
    )

    # Latest imported resume (guard in case 'is_imported' doesn't exist)
    try:
        imported_resume = (
            Resume.objects.filter(user=request.user, is_imported=True)
            .order_by("-created_at")
            .first()
        )
    except Exception:
        imported_resume = None

    # Canonical "latest" resume for other sections
    resume = Resume.objects.filter(user=request.user).order_by("-created_at").first()

    # Children of resume (OK if resume is None)
    education_entries = Education.objects.filter(resume=resume) if resume else []
    experience_entries = Experience.objects.filter(resume=resume) if resume else []

    # User's job applications
    applications = Application.objects.filter(applicant=request.user)

    # Onboarding progress: Complete Profile, Create Resume, Saved Jobs
    saved_jobs_count = SavedJob.objects.filter(user=request.user).count()
    steps = {
        "profile": bool(user_profile.bio or user_profile.profile_picture),
        "resume": bool(resume),
        "saved_jobs": saved_jobs_count > 0,
    }
    steps_completed = sum(1 for k in steps if steps[k])
    completion_percentage = int((steps_completed / 3) * 100)
    # Determine the current (next) step name for highlighting
    step_order = ["profile", "resume", "saved_jobs"]
    current_step = next((name for name in step_order if not steps.get(name)), None)

    # Suggested jobs: only attempt if we detect skills and jobs are live
    skills_list = extract_resume_skills(resume)
    suggested_jobs = match_jobs_for_user(request.user)[:10] if (jobs_live and skills_list) else []

    # Compute a lightweight match % for suggested jobs (if skills available)
    suggested_cards = []
    try:
        if suggested_jobs and skills_list:
            user_skills = {s.strip().lower() for s in skills_list}
            for job in suggested_jobs:
                try:
                    job_skills = {s.name.strip().lower() for s in job.skills_required.all()}
                except Exception:
                    job_skills = set()
                percent = None
                if job_skills:
                    overlap = len(user_skills & job_skills)
                    percent = int(round(100 * overlap / max(1, len(job_skills))))
                suggested_cards.append({"job": job, "match": percent, "source": "matched"})
        else:
            suggested_cards = [{"job": j, "match": None, "source": "matched"} for j in (suggested_jobs or [])]
    except Exception:
        suggested_cards = [{"job": j, "match": None, "source": "matched"} for j in (suggested_jobs or [])]

    # Invitations: surface as "Invited to Apply"
    invited_cards = []
    try:
        from reroute_business.job_list.models import JobInvitation
        invited_qs = (
            JobInvitation.objects
            .filter(candidate=request.user, job__is_active=True)
            .select_related('job')
            .order_by('-created_at')
        )
        invited_cards = [{"job": inv.job, "match": None, "source": "invited"} for inv in invited_qs]
    except Exception:
        invited_cards = []

    if invited_cards:
        invited_job_ids = {c['job'].id for c in invited_cards}
        suggested_cards = invited_cards + [c for c in suggested_cards if c['job'].id not in invited_job_ids]

    has_invites = any(c.get('source') == 'invited' for c in suggested_cards)

    # Friendly join date string
    joined_date = request.user.date_joined.strftime("%b %d, %Y") if request.user.date_joined else None

    # Notifications (direct + broadcast)
    try:
        from .models import Notification
        is_emp = bool(getattr(user_profile, 'is_employer', False))
        from django.db.models import Q
        broadcast_filters = Q(user__isnull=True) & (
            Q(target_group=Notification.TARGET_ALL) |
            Q(target_group=Notification.TARGET_EMPLOYERS if is_emp else Notification.TARGET_SEEKERS)
        )
        notifications = (
            Notification.objects
            .filter(Q(user=request.user) | broadcast_filters)
            .order_by('-created_at', '-id')
        )
    except Exception:
        notifications = []

    # ---- Key metrics for Stats card ----
    applications_sent = applications.count()
    matches_found = len(suggested_jobs) if suggested_jobs else 0
    profile_views = 0
    try:
        from reroute_business.core.models import AnalyticsEvent
        # Prefer explicit profile_view events
        q = AnalyticsEvent.objects.filter(event_type="profile_view")
        try:
            profile_views = q.filter(metadata__viewed_user=request.user.username).count()
        except Exception:
            # Fallback to path-based match
            profile_views = AnalyticsEvent.objects.filter(
                event_type="page_view",
                path__icontains=f"/profiles/view/{request.user.username}/",
            ).count()
    except Exception:
        profile_views = 0

    # Scheduled interviews for this user (tolerant: exclude only canceled)
    try:
        from .models import Interview
        upcoming_qs = (
            Interview.objects
            .select_related('job', 'employer')
            .filter(candidate=request.user)
            .exclude(status=Interview.STATUS_CANCELED)
            .order_by('scheduled_at', 'id')
        )
        # If you prefer future-only, uncomment this line
        # upcoming_qs = upcoming_qs.filter(scheduled_at__gte=timezone.now())
        upcoming_interviews = list(upcoming_qs[:8])
    except Exception:
        upcoming_interviews = []

    # Learning modules + recent video-to-module recommendations.
    try:
        module_qs = Module.objects.annotate(quiz_count=Count("questions")).order_by('-created_at')
        recommended_modules = list(module_qs[:6])
        recent_module = recommended_modules[0] if recommended_modules else None

        module_by_youtube_id = {}
        for module in module_qs:
            vid = _extract_youtube_id(getattr(module, "video_url", "") or "")
            if vid:
                module_by_youtube_id[vid] = module

        recent_window = timezone.now() - timedelta(days=2)
        video_candidates = list(
            YouTubeVideo.objects.filter(created_at__gte=recent_window).order_by("-created_at")[:20]
        )
        if not video_candidates:
            video_candidates = list(YouTubeVideo.objects.order_by("-created_at")[:20])

        recommended_learning_items = []
        seen_module_ids = set()

        # Prefer newest videos that map to modules with quiz questions.
        for video in video_candidates:
            yid = _extract_youtube_id(getattr(video, "video_url", "") or "")
            mapped_module = module_by_youtube_id.get(yid)
            if not mapped_module or mapped_module.quiz_count <= 0 or mapped_module.id in seen_module_ids:
                continue

            seen_module_ids.add(mapped_module.id)
            recommended_learning_items.append(
                {
                    "title": mapped_module.title,
                    "description": mapped_module.description or video.description,
                    "url": reverse("module_detail", args=[mapped_module.pk]),
                    "cta_label": "Open module + quiz",
                    "meta": "From recent video uploads",
                }
            )
            if len(recommended_learning_items) >= 4:
                break

        # Fill remaining spots with existing quiz-enabled modules.
        if len(recommended_learning_items) < 4:
            for module in module_qs:
                if module.quiz_count <= 0 or module.id in seen_module_ids:
                    continue
                seen_module_ids.add(module.id)
                recommended_learning_items.append(
                    {
                        "title": module.title,
                        "description": module.description,
                        "url": reverse("module_detail", args=[module.pk]),
                        "cta_label": "Open module + quiz",
                        "meta": "Recommended module",
                    }
                )
                if len(recommended_learning_items) >= 4:
                    break

        # Final fallback: show recent videos if no quiz-backed modules were found.
        if not recommended_learning_items:
            for video in video_candidates[:4]:
                recommended_learning_items.append(
                    {
                        "title": video.title,
                        "description": video.description,
                        "url": reverse("video_watch", args=[video.pk]),
                        "cta_label": "Watch video",
                        "meta": "Video recommendation",
                    }
                )
    except Exception:
        recommended_modules = []
        recent_module = None
        recommended_learning_items = []

    # Reentry organizations catalog picks (verified only)
    try:
        recommended_orgs = list(
            ReentryOrganization.objects.filter(is_verified=True).order_by('name')[:6]
        )
    except Exception:
        recommended_orgs = []

    modules_completed = 0
    try:
        from reroute_business.resources.models import ModuleQuizScore
        modules_completed = ModuleQuizScore.objects.filter(user=request.user).count()
    except Exception:
        modules_completed = 0
    modules_completed_percent = min(modules_completed * 20, 100) if modules_completed else 0

    try:
        saved_orgs_qs = SavedOrganization.objects.filter(user=request.user).select_related('organization')
        organizations_saved_count = saved_orgs_qs.count()
        saved_org_ids = [o.organization_id for o in saved_orgs_qs]
    except Exception:
        organizations_saved_count = 0
        saved_org_ids = []

    # Charts for seeker dashboard were removed per request.

    # Sync onboarding flags (early access priority)
    try:
        user_profile.update_onboarding_flags(resume=resume)
        user_profile.save(update_fields=["onboarding_step", "onboarding_completed", "early_access_priority"])
    except Exception:
        pass

    profile_complete = user_profile.profile_is_complete()
    resume_complete = user_profile.resume_is_complete(resume=resume)
    modules_started = modules_completed > 0

    readiness_score = 0
    readiness_score += 35 if resume_complete else 0
    readiness_score += 35 if profile_complete else (15 if (user_profile.bio or user_profile.profile_picture) else 0)
    readiness_score += 15 if modules_started else 0
    readiness_score += 15 if organizations_saved_count > 0 else 0
    readiness_percent = min(100, readiness_score)

    if readiness_percent < 100:
        hero_cta_label = "Complete Your Profile"
        hero_cta_url = f"{reverse('settings')}?panel=profile"
    elif jobs_live:
        hero_cta_label = "View opportunities"
        hero_cta_url = reverse('opportunities')
    else:
        hero_cta_label = "View dashboard"
        hero_cta_url = reverse('dashboard:user')

    notify_jobs_live = bool(request.session.get("notify_jobs_live", False))
    notify_job_matches = bool(request.session.get("notify_job_matches", False))
    benefit_finder_completed = bool(request.session.get("benefit_finder_completed", False))

    progress_items = [
        {
            "label": "Resume uploaded",
            "subtext": "Looking great" if resume_complete else "Upload to unlock matches",
            "url": reverse("resumes:resume_landing"),
            "done": resume_complete,
        },
        {
            "label": "Learning module started",
            "subtext": f"{modules_completed} of 3 completed" if modules_completed else "Start your first module",
            "url": f"{reverse('resource_list')}#modules",
            "done": modules_started,
        },
        {
            "label": "Organizations saved",
            "subtext": "Find support near you",
            "url": reverse("reentry_org:organization_catalog"),
            "done": organizations_saved_count > 0,
        },
    ]

    # Log first dashboard visit for onboarding
    try:
        log_onboarding_event(request.user, "onboarding_started", once=True)
    except Exception:
        pass

    return render(request, 'dashboard/user_dashboard.html', {
        'profile': user_profile,
        'resume': resume,
        'imported_resume': imported_resume,
        'education_entries': education_entries,
        'experience_entries': experience_entries,
        'applications': applications,
        'completion_percentage': completion_percentage,
        'steps_completed': steps_completed,
        'onboarding_steps': steps,
        'current_step': current_step,
        'joined_date': joined_date,
        'suggested_jobs': suggested_jobs,
        'suggested_cards': suggested_cards,
        'has_invites': has_invites,
        'notifications': notifications,
        'stats': {
            'applications_sent': applications_sent,
            'profile_views': profile_views,
            'matches_found': matches_found,
        },
        'upcoming_interviews': upcoming_interviews,
        'recommended_modules': recommended_modules,
        'recent_module': recent_module,
        'recommended_learning_items': recommended_learning_items,
        'recommended_orgs': recommended_orgs,
        'modules_completed': modules_completed,
        'modules_completed_percent': modules_completed_percent,
        'saved_jobs_count': saved_jobs_count,
        'organizations_saved_count': organizations_saved_count,
        'saved_org_ids': saved_org_ids,
        'early_access_mode': early_access_mode,
        'jobs_live': jobs_live,
        'early_access_message': early_access_message,
        'hero_cta_label': hero_cta_label,
        'hero_cta_url': hero_cta_url,
        'readiness_percent': readiness_percent,
        'progress_items': progress_items,
        'profile_complete': profile_complete,
        'resume_complete': resume_complete,
        'notify_jobs_live': notify_jobs_live,
        'notify_job_matches': notify_job_matches,
        'benefit_finder_completed': benefit_finder_completed,
    })


@login_required
@require_POST
def toggle_job_notifications(request):
    pref = (request.POST.get("pref") or "jobs_live").strip().lower()
    key = "notify_jobs_live" if pref == "jobs_live" else "notify_job_matches"
    current = bool(request.session.get(key, False))
    request.session[key] = not current
    request.session.modified = True

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return _json_ok({"preference": key, "enabled": request.session[key]})
    return redirect("dashboard:user")


# =========================
# Saved & Matched Jobs
# =========================
@login_required
def saved_jobs_view(request):
    """My Jobs hub: Saved / Applied / Archived (tabs via ?tab=)."""
    tab = (request.GET.get('tab') or 'saved').lower()
    if tab not in {'saved', 'applied', 'archived'}:
        tab = 'saved'

    saved_jobs = (
        SavedJob.objects
        .filter(user=request.user)
        .select_related('job', 'job__employer')
        .order_by('-saved_at')
    )
    applied_jobs = (
        Application.objects
        .filter(applicant=request.user)
        .select_related('job', 'job__employer')
        .order_by('-submitted_at')
    )
    try:
        archived_jobs = (
            ArchivedJob.objects
            .filter(user=request.user)
            .select_related('job', 'job__employer')
            .order_by('-archived_at')
        )
    except ProgrammingError:
        # Table not migrated yet (e.g., deploy lag). Fallback to empty list.
        archived_jobs = []

    return render(request, 'dashboard/saved_jobs.html', {
        'saved_jobs': saved_jobs,
        'applied_jobs': applied_jobs,
        'active_tab': tab,
        'archived_jobs': archived_jobs,
    })


@login_required
@require_POST
def archive_saved_job(request):
    """Move a SavedJob to ArchivedJob for the current user."""
    job_id = request.POST.get('job_id')
    if not job_id:
        messages.error(request, 'Invalid job.')
        return redirect(f"{reverse('dashboard:saved_jobs')}?tab=saved")

    saved = SavedJob.objects.filter(user=request.user, job_id=job_id).select_related('job').first()
    if not saved:
        messages.error(request, 'Saved job not found.')
        return redirect(f"{reverse('dashboard:saved_jobs')}?tab=saved")

    # Create archived (ignore if already archived)
    ArchivedJob.objects.get_or_create(user=request.user, job=saved.job)
    saved.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'job_id': int(job_id)})
    messages.success(request, 'Job archived.')
    return redirect(f"{reverse('dashboard:saved_jobs')}?tab=archived")


@login_required
@require_POST
def unarchive_job(request):
    """Move an ArchivedJob back to SavedJob for the current user."""
    job_id = request.POST.get('job_id')
    if not job_id:
        messages.error(request, 'Invalid job.')
        return redirect(f"{reverse('dashboard:saved_jobs')}?tab=archived")

    archive = ArchivedJob.objects.filter(user=request.user, job_id=job_id).select_related('job').first()
    if not archive:
        messages.error(request, 'Archived job not found.')
        return redirect(f"{reverse('dashboard:saved_jobs')}?tab=archived")

    SavedJob.objects.get_or_create(user=request.user, job=archive.job)
    archive.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'job_id': int(job_id)})
    messages.success(request, 'Job moved back to Saved.')
    return redirect(f"{reverse('dashboard:saved_jobs')}?tab=saved")

@login_required
def matched_jobs_view(request):
    """Render nearby jobs with skill-overlap badges when available."""
    try:
        radius = int(request.GET.get('radius') or 25)
    except ValueError:
        radius = 25

    profile = getattr(request.user, "profile", None)
    selected_zip = (getattr(profile, "zip_code", "") or "").strip()
    nearby_prompt = ""

    if profile and getattr(profile, "geo_point", None):
        matched_jobs = list(
            get_nearby_jobs(profile, miles=radius)
            .select_related("employer")
            .prefetch_related("skills_required")
        )
    else:
        if any(f.name == "is_remote" for f in Job._meta.get_fields()):
            matched_jobs = list(
                Job.objects.filter(is_active=True, is_remote=True)
                .select_related("employer")
                .prefetch_related("skills_required")
                .order_by("-created_at")
            )
        else:
            matched_jobs = []
        nearby_prompt = "Add your ZIP code to see jobs near you."

    # Compute skill-overlap badges per job
    resume = Resume.objects.filter(user=request.user).order_by('-created_at').first()
    overlap_by_job: dict[int, list[str]] = {}
    if resume and resume.skills.exists():
        user_skills = {s.name.strip().lower(): s.name for s in resume.skills.all()}
        for job in matched_jobs:
            job_skills = {s.name.strip().lower(): s.name for s in job.skills_required.all()}
            overlap_keys = set(user_skills.keys()) & set(job_skills.keys())
            overlap_by_job[job.id] = [job_skills[k] for k in overlap_keys]

    items = [
        {"job": job, "overlap": overlap_by_job.get(job.id, [])}
        for job in matched_jobs
    ]

    return render(request, 'dashboard/matched_jobs.html', {
        'items': items,
        'selected_zip': selected_zip,
        'selected_radius': radius,
        'nearby_prompt': nearby_prompt,
    })


# =========================
# Employer Dashboard & Analytics
# =========================
@login_required
def employer_dashboard(request):
    """
    MVP employer dashboard.
    Job.employer is a ForeignKey to User, so filter directly with request.user.
    """
    employer_user = request.user

    # Ensure EmployerProfile exists (optional: not strictly required for counts)
    try:
        from reroute_business.profiles.models import EmployerProfile
        EmployerProfile.objects.get_or_create(user=employer_user)
    except Exception:
        pass

    # Jobs "owned" by this employer, with simple sort control
    sort_by = (request.GET.get('sort_by') or 'newest').lower()
    order = '-created_at' if sort_by == 'newest' else 'created_at'
    jobs = Job.objects.filter(employer=employer_user).order_by(order)

    # Recent in-app notifications for this employer (include broadcasts)
    try:
        from .models import Notification
        from django.db.models import Q
        broadcast = Q(user__isnull=True) & (
            Q(target_group=Notification.TARGET_ALL) | Q(target_group=Notification.TARGET_EMPLOYERS)
        )
        notifications = (
            Notification.objects
            .filter(Q(user=employer_user) | broadcast)
            .order_by('-created_at', '-id')[:10]
        )
    except Exception:
        notifications = []
    # Upcoming interviews for this employer
    try:
        from .models import Interview
        from django.db.models import Q
        # Be tolerant: include records tied either via Interview.employer OR Job.employer
        # and exclude only canceled interviews.
        interview_qs = (
            Interview.objects
            .filter(
                Q(employer=employer_user) | Q(job__employer=employer_user),
            )
            .exclude(status=Interview.STATUS_CANCELED)
            .select_related('job', 'candidate')
            .order_by('scheduled_at', 'id')
            .distinct()  # guard against duplicates if both conditions match
        )
        # If you want only upcoming, uncomment the line below
        # interview_qs = interview_qs.filter(scheduled_at__gte=timezone.now())
        interviews = list(interview_qs[:50])
    except Exception:
        interviews = []

    # Basic analytics (live numbers)
    total_jobs = Job.objects.filter(employer=employer_user).count()
    active_jobs = Job.objects.filter(employer=employer_user, is_active=True).count()
    apps_qs = Application.objects.filter(job__employer=employer_user)
    total_applications = apps_qs.count()
    # Treat "filled" as inactive jobs for this dashboard
    jobs_filled = Job.objects.filter(employer=employer_user, is_active=False).count()

    analytics = {
        "jobs_posted": total_jobs,
        "active_jobs": active_jobs,
        "total_applicants": total_applications,
        "jobs_filled": jobs_filled,
    }

    status_counts = {
        row["status"]: row["c"]
        for row in apps_qs.values("status").annotate(c=Count("id"))
    }
    pipeline_counts = {
        "new": status_counts.get("pending", 0),
        "under_review": status_counts.get("reviewed", 0),
        "interview": status_counts.get("interview", 0),
        "decision": status_counts.get("accepted", 0) + status_counts.get("rejected", 0),
    }

    recent_applications = list(
        apps_qs.select_related("applicant", "job").order_by("-submitted_at")[:6]
    )

    # Employer verification flag (controls alert banner)
    employer_verified = False
    try:
        from reroute_business.profiles.models import EmployerProfile as _EP
        ep = _EP.objects.filter(user=employer_user).first()
        employer_verified = bool(getattr(ep, 'verified', False)) if ep else False
    except Exception:
        employer_verified = False

    return render(request, 'dashboard/employer_dashboard.html', {
        'jobs': jobs,
        'notifications': notifications,
        'interviews': interviews,
        'analytics': analytics,
        'pipeline_counts': pipeline_counts,
        'recent_applications': recent_applications,
        # Expose individual variables for template clarity
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'total_applications': total_applications,
        'jobs_filled': jobs_filled,
        'sort_by': sort_by,
        'employer_verified': employer_verified,
    })


@login_required
def employer_job_postings(request):
    employer_user = request.user
    jobs = Job.objects.filter(employer=employer_user).order_by('-created_at')
    total_jobs = jobs.count()
    live_jobs = jobs.filter(is_active=True).count()
    closed_jobs = jobs.filter(is_active=False).count()
    draft_jobs = 0
    pending_jobs = 0

    employer_verified = False
    try:
        from reroute_business.profiles.models import EmployerProfile as _EP
        ep = _EP.objects.filter(user=employer_user).first()
        employer_verified = bool(getattr(ep, 'verified', False)) if ep else False
    except Exception:
        employer_verified = False

    return render(request, 'dashboard/employer_job_postings.html', {
        'jobs': jobs,
        'total_jobs': total_jobs,
        'live_jobs': live_jobs,
        'closed_jobs': closed_jobs,
        'draft_jobs': draft_jobs,
        'pending_jobs': pending_jobs,
        'employer_verified': employer_verified,
    })


@login_required
def employer_applicants(request):
    employer_user = request.user
    apps_qs = (
        Application.objects
        .filter(job__employer=employer_user)
        .select_related('applicant', 'job')
        .order_by('-submitted_at')
    )

    status_counts = {
        row["status"]: row["c"]
        for row in apps_qs.values("status").annotate(c=Count("id"))
    }
    pipeline_counts = {
        "all": apps_qs.count(),
        "new": status_counts.get("pending", 0),
        "under_review": status_counts.get("reviewed", 0),
        "interview": status_counts.get("interview", 0),
        "decision": status_counts.get("accepted", 0) + status_counts.get("rejected", 0),
    }

    return render(request, 'dashboard/employer_applicants.html', {
        'applications': apps_qs[:20],
        'pipeline_counts': pipeline_counts,
    })


@login_required
@require_POST
def employer_application_update_status(request, app_id: int):
    app = Application.objects.select_related('job').filter(id=app_id, job__employer=request.user).first()
    if not app:
        return _json_err({'application': 'Not found.'}, status=404)

    new_status = (request.POST.get('status') or '').strip()
    if new_status == 'decision':
        new_status = 'accepted'

    valid = {s for s, _ in getattr(Application, 'STATUS_CHOICES', [])}
    if new_status not in valid:
        return _json_err({'status': 'Invalid status.'}, status=400)

    app.status = new_status
    app.save(update_fields=['status', 'updated_at'])
    return _json_ok({'status': new_status})


@login_required
@require_POST
def employer_application_update_notes(request, app_id: int):
    app = Application.objects.select_related('job').filter(id=app_id, job__employer=request.user).first()
    if not app:
        return _json_err({'application': 'Not found.'}, status=404)

    notes = (request.POST.get('notes') or '').strip()
    app.notes = notes
    app.save(update_fields=['notes', 'updated_at'])
    return _json_ok({'notes': notes})


@login_required
def employer_company_profile(request):
    from reroute_business.profiles.forms import EmployerCompanyProfileForm
    from reroute_business.profiles.models import EmployerProfile

    employer_profile, _ = EmployerProfile.objects.get_or_create(
        user=request.user,
        defaults={'company_name': request.user.get_full_name() or request.user.username},
    )

    if request.method == "POST":
        form = EmployerCompanyProfileForm(request.POST, instance=employer_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Company profile updated.")
            return redirect('dashboard:employer_company_profile')
    else:
        form = EmployerCompanyProfileForm(instance=employer_profile)

    return render(request, 'dashboard/employer_company_profile.html', {
        'form': form,
        'employer_profile': employer_profile,
    })


@login_required
def employer_fair_chance_guide(request):
    return render(request, 'dashboard/employer_fair_chance_guide.html')


@login_required
def employer_browse_returning_citizens(request):
    if not is_employer(request.user):
        messages.error(request, "You do not have access to that page.")
        return redirect('dashboard:my_dashboard')

    from reroute_business.job_list.models import Job, JobInvitation
    try:
        from reroute_business.resumes.models import Resume
    except Exception:
        Resume = None

    active_jobs = Job.objects.filter(employer=request.user, is_active=True).order_by('-created_at')

    profiles_qs = (
        UserProfile.objects.select_related('user')
        .prefetch_related('skills')
        .filter(account_status='active', user__is_active=True)
        .exclude(user=request.user)
        .filter(user__employerprofile__isnull=True)
        .exclude(user__groups__name__in=['Employer', 'Employers'])
    )

    search = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or '').strip()
    location = (request.GET.get('location') or '').strip()
    skill = (request.GET.get('skill') or '').strip()
    cert = (request.GET.get('cert') or '').strip()
    invited_filter = (request.GET.get('invited') or '').strip()
    ready_only = (request.GET.get('ready') or '').strip()

    if status:
        profiles_qs = profiles_qs.filter(status=status)
    if ready_only in {'1', 'true', 'yes', 'on'}:
        profiles_qs = profiles_qs.filter(ready_to_discuss_background=True)
    if location:
        profiles_qs = profiles_qs.filter(
            Q(city__icontains=location) |
            Q(state__icontains=location) |
            Q(zip_code__icontains=location) |
            Q(street_address__icontains=location)
        )
    if search:
        profiles_qs = profiles_qs.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(preferred_name__icontains=search) |
            Q(city__icontains=search) |
            Q(state__icontains=search) |
            Q(zip_code__icontains=search) |
            Q(skills__name__icontains=search) |
            Q(user__resume_resumes__skills__name__icontains=search)
        )
    if skill:
        profiles_qs = profiles_qs.filter(
            Q(skills__name__icontains=skill) |
            Q(user__resume_resumes__skills__name__icontains=skill)
        )
    if cert and Resume:
        resume_user_ids = Resume.objects.filter(certifications__icontains=cert).values_list('user_id', flat=True)
        profiles_qs = profiles_qs.filter(user_id__in=resume_user_ids)

    profiles_qs = profiles_qs.distinct()

    invited_ids = set(
        JobInvitation.objects.filter(employer=request.user).values_list('candidate_id', flat=True)
    )
    if invited_filter == 'invited':
        profiles_qs = profiles_qs.filter(user_id__in=invited_ids)
    elif invited_filter == 'not_invited':
        profiles_qs = profiles_qs.exclude(user_id__in=invited_ids)

    profiles_qs = profiles_qs.order_by('user__first_name', 'user__last_name', 'user__username')

    paginator = Paginator(profiles_qs, 12)
    page_number = request.GET.get('page') or 1
    page_obj = paginator.get_page(page_number)

    profiles = list(page_obj.object_list)
    user_ids = [p.user_id for p in profiles]

    resume_by_user = {}
    if Resume and user_ids:
        resumes = (
            Resume.objects.filter(user_id__in=user_ids)
            .order_by('user_id', '-created_at')
            .prefetch_related('skills', 'experiences', 'experience_entries')
        )
        for res in resumes:
            if res.user_id not in resume_by_user:
                resume_by_user[res.user_id] = res

    candidates = []
    for profile in profiles:
        user = profile.user
        resume = resume_by_user.get(profile.user_id)
        display_first = (profile.firstname or user.first_name or '').strip()
        display_last = (profile.lastname or user.last_name or '').strip()
        display_name = (profile.preferred_name or f"{display_first} {display_last}".strip() or user.username)
        initials = ''.join([part[0] for part in display_name.split()[:2] if part]).upper() or user.username[:1].upper()

        headline = (getattr(profile, "headline", "") or "").strip()
        if not headline and resume:
            headline = (resume.headline or resume.summary or '').strip()
        if not headline:
            headline = "Motivated candidate"

        bio = (profile.bio or (resume.summary if resume else '') or '').strip()

        skills_qs = list(profile.skills.all())
        if not skills_qs and resume:
            skills_qs = list(resume.skills.all())
        skill_names = [s.name for s in skills_qs if getattr(s, 'name', '').strip()]
        skills_display = skill_names[:4]
        skills_more = max(0, len(skill_names) - len(skills_display))

        roles_count = 0
        certs_count = 0
        if resume:
            try:
                roles_count = resume.experiences.count() + resume.experience_entries.count()
            except Exception:
                roles_count = 0
            certs_raw = (resume.certifications or '').splitlines()
            certs_count = len([ln for ln in certs_raw if ln.strip()])

        skills_count = len(skill_names)

        location_line = (getattr(profile, "location", "") or "").strip()
        if not location_line:
            if profile.city or profile.state:
                location_line = f"{profile.city or ''}{', ' if profile.city and profile.state else ''}{profile.state or ''}".strip(', ')
            elif profile.zip_code:
                location_line = profile.zip_code

        status_label = profile.get_status_display() if profile.status else "Status not set"

        candidates.append({
            'id': user.id,
            'username': user.username,
            'display_name': display_name,
            'initials': initials,
            'profile_picture': profile.profile_picture.url if profile.profile_picture else '',
            'headline': headline,
            'status_label': status_label,
            'location': location_line,
            'bio': bio,
            'skills': skills_display,
            'skills_more': skills_more,
            'roles_count': roles_count,
            'certs_count': certs_count,
            'skills_count': skills_count,
            'ready_to_discuss_background': bool(getattr(profile, 'ready_to_discuss_background', False)),
            'invited': user.id in invited_ids,
        })

    return render(request, 'dashboard/employer_browse_returning_citizens.html', {
        'candidates': candidates,
        'active_jobs': active_jobs,
        'total_candidates': paginator.count,
        'page_obj': page_obj,
        'filters': {
            'q': search,
            'status': status,
            'location': location,
            'skill': skill,
            'cert': cert,
            'invited': invited_filter,
            'ready': ready_only,
        },
        'status_choices': UserProfile._meta.get_field('status').choices,
    })


@login_required
@require_POST
def employer_send_invitation(request):
    if not is_employer(request.user):
        return _json_err({'permission': 'Not allowed.'}, status=403)

    from django.contrib.auth.models import User
    from reroute_business.job_list.models import Job, JobInvitation
    try:
        candidate_id = int(request.POST.get('candidate_id') or 0)
        job_id = int(request.POST.get('job_id') or 0)
    except (TypeError, ValueError):
        candidate_id = 0
        job_id = 0

    if not candidate_id or not job_id:
        return _json_err({'fields': 'Candidate and job are required.'}, status=400)

    job = Job.objects.filter(id=job_id, employer=request.user, is_active=True).first()
    if not job:
        return _json_err({'job': 'Please select an active job listing.'}, status=400)

    candidate = User.objects.filter(id=candidate_id, is_active=True).first()
    if not candidate:
        return _json_err({'candidate': 'Candidate not found.'}, status=404)

    # Ensure candidate is not an employer
    try:
        if hasattr(candidate, 'employerprofile') and candidate.employerprofile:
            return _json_err({'candidate': 'Cannot invite employer accounts.'}, status=400)
    except Exception:
        pass

    if JobInvitation.objects.filter(employer=request.user, candidate=candidate, job=job).exists():
        return _json_err({'duplicate': 'Invitation already sent.'}, status=409)

    message = (request.POST.get('message') or '').strip()
    invite = JobInvitation.objects.create(
        employer=request.user,
        candidate=candidate,
        job=job,
        message=message,
    )

    return _json_ok({'invitation_id': invite.id})


@login_required
def employer_job_matches(request, job_id: int):
    """
    Show all matched candidates for a specific job owned by the employer.
    """
    job = Job.objects.filter(id=job_id, employer=request.user).first()
    if not job:
        messages.error(request, 'Job not found or not owned by you.')
        return redirect('dashboard:employer')

    # Use existing matcher and filter to this job, with a large per-job limit
    from reroute_business.job_list.matching import match_seekers_for_employer
    items = [
        it for it in match_seekers_for_employer(request.user, limit_per_job=200)
        if it.get('job') and it['job'].id == job.id
    ]
    return render(request, 'dashboard/employer_job_matches.html', {
        'job': job,
        'items': items,
    })


@login_required
def employer_matcher(request):
    """Overall matcher view: grouped matches for all of this employer's jobs."""
    from reroute_business.job_list.matching import match_seekers_for_employer
    # We only need previews here, so fetch top 3 per job for efficiency
    items = match_seekers_for_employer(request.user, limit_per_job=3)

    # Build simple blocks the template can iterate without dict lookups
    job_blocks = []
    seen_job_ids = set()
    for it in items:
        job = it.get('job')
        if not job or job.id in seen_job_ids:
            continue
        # Collect candidates for this job from the "items" list (already limited per job)
        candidates = [x for x in items if x.get('job') and x['job'].id == job.id]
        job_blocks.append({
            'job': job,
            'candidates': candidates,
        })
        seen_job_ids.add(job.id)

    # Ensure we show jobs with no matches as well
    from reroute_business.job_list.models import Job as _Job
    employer_jobs = list(_Job.objects.filter(employer=request.user).order_by('-created_at'))
    matched_job_ids = {b['job'].id for b in job_blocks}
    for j in employer_jobs:
        if j.id not in matched_job_ids:
            job_blocks.append({'job': j, 'candidates': []})

    # Preserve a sensible order: newest jobs first
    job_blocks.sort(key=lambda b: getattr(b['job'], 'created_at', None) or 0, reverse=True)

    return render(request, 'dashboard/employer_matcher.html', {
        'job_blocks': job_blocks,
    })


# =========================
# Notifications
# =========================
from django.views.decorators.http import require_http_methods, require_GET
from django.http import JsonResponse
from django.utils.timezone import now as tz_now
from django.db.models.functions import TruncDate
from django.db.models import Count

@login_required
@require_http_methods(["GET", "POST"])
def notifications_view(request):
    """List notifications and allow marking all as read via POST."""
    from .models import Notification

    if request.method == 'POST':
        action = (request.POST.get('action') or '').strip()
        if action == 'mark_all_read':
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, 'action': 'mark_all_read'})
            messages.success(request, 'All notifications marked as read.')
            return redirect('dashboard:notifications')
        elif action == 'mark_read':
            # Mark a single notification as read (if owned by user)
            try:
                nid = int(request.POST.get('id') or 0)
            except (TypeError, ValueError):
                nid = 0
            if nid:
                updated = Notification.objects.filter(id=nid, user=request.user).update(is_read=True)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    if updated:
                        return JsonResponse({'ok': True, 'id': nid})
                    return JsonResponse({'ok': False, 'id': nid, 'error': 'Not found or not owned'}, status=404)
                if updated:
                    messages.success(request, 'Notification marked as read.')
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': 'Invalid id'}, status=400)
            return redirect('dashboard:notifications')

    # Include broadcasts in the notifications page
    from django.db.models import Q
    is_emp = False
    try:
        # Try to infer employment role (if profiles app present)
        from reroute_business.profiles.models import UserProfile
        up = UserProfile.objects.filter(user=request.user).first()
        is_emp = bool(getattr(up, 'is_employer', False))
    except Exception:
        pass
    bcast = Q(user__isnull=True) & (
        Q(target_group=Notification.TARGET_ALL) |
        Q(target_group=Notification.TARGET_EMPLOYERS if is_emp else Notification.TARGET_SEEKERS)
    )
    notes = Notification.objects.filter(Q(user=request.user) | bcast).order_by('-created_at', '-id')
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return render(request, 'dashboard/notifications.html', {
        'notifications': notes,
        'unread_count': unread_count,
    })


# =========================
# User Interviews: Modal + Actions
# =========================
@login_required
@require_GET
def user_interviews_modal(request):
    """Return the HTML for the user's interviews modal (non-canceled)."""
    from .models import Interview
    interviews = (
        Interview.objects
        .select_related('job', 'employer')
        .filter(candidate=request.user)
        .exclude(status=Interview.STATUS_CANCELED)
        .order_by('scheduled_at', 'id')
    )
    return render(request, 'dashboard/partials/user_interviews_modal.html', {
        'interviews': interviews,
    })


@login_required
@require_POST
def user_accept_interview(request):
    """Candidate accepts interview: send a notification to the employer."""
    from .models import Interview, Notification
    iid = request.POST.get('interview_id')
    iv = Interview.objects.select_related('job', 'employer', 'candidate').filter(id=iid, candidate=request.user).first()
    if not iv:
        return JsonResponse({'ok': False, 'error': 'Interview not found'}, status=404)
    # Notify employer
    try:
        Notification.objects.create(
            user=iv.employer,
            title='Interview Accepted',
            message=f"{request.user.get_full_name() or request.user.username} accepted the interview for '{iv.job.title}' on {iv.scheduled_at:%b %d, %Y %I:%M %p}.",
            job=iv.job,
            url='',
        )
    except Exception:
        pass
    # Email employer
    try:
        from django.core.mail import send_mail
        when_str = iv.scheduled_at.strftime('%b %d, %Y %I:%M %p')
        send_mail(
            subject=f"Interview Accepted: {iv.job.title}",
            message=(
                f"{request.user.get_full_name() or request.user.username} accepted the interview for '{iv.job.title}'.\n"
                f"When: {when_str}.\n\n"
                f"You can coordinate further from your Employer Dashboard."
            ),
            from_email=None,
            recipient_list=[iv.employer.email],
            fail_silently=True,
        )
    except Exception:
        pass
    return JsonResponse({'ok': True})


@login_required
@require_POST
def user_request_reschedule(request):
    """Candidate requests reschedule: notify employer with optional suggestion."""
    from .models import Interview, Notification
    iid = request.POST.get('interview_id')
    suggested = (request.POST.get('datetime') or '').strip()
    reason = (request.POST.get('message') or '').strip()
    iv = Interview.objects.select_related('job', 'employer', 'candidate').filter(id=iid, candidate=request.user).first()
    if not iv:
        return JsonResponse({'ok': False, 'error': 'Interview not found'}, status=404)
    parts = [
        f"{request.user.get_full_name() or request.user.username} requested a reschedule for '{iv.job.title}'.",
        f"Current: {iv.scheduled_at:%b %d, %Y %I:%M %p}."
    ]
    if suggested:
        parts.append(f"Suggested: {suggested}.")
    if reason:
        parts.append(f"Note: {reason}")
    try:
        Notification.objects.create(
            user=iv.employer,
            title='Interview Reschedule Request',
            message=' '.join(parts),
            job=iv.job,
            url='',
        )
    except Exception:
        pass
    # Email employer
    try:
        from django.core.mail import send_mail
        when_str = iv.scheduled_at.strftime('%b %d, %Y %I:%M %p')
        body_lines = [
            f"{request.user.get_full_name() or request.user.username} requested a reschedule for '{iv.job.title}'.",
            f"Current: {when_str}."
        ]
        if suggested:
            body_lines.append(f"Suggested: {suggested}.")
        if reason:
            body_lines.append(f"Note: {reason}")
        send_mail(
            subject=f"Reschedule Requested: {iv.job.title}",
            message='\n'.join(body_lines),
            from_email=None,
            recipient_list=[iv.employer.email],
            fail_silently=True,
        )
    except Exception:
        pass
    return JsonResponse({'ok': True})


@login_required
def employer_analytics(request):
    """
    Employer Analytics page.
    - Renders a full page with metrics + charts on normal requests
    - Returns JSON datasets when requested via AJAX (for time-range changes)
    """
    employer_user = request.user

    # Base job + application querysets for this employer
    jobs_qs = Job.objects.filter(employer=employer_user)
    apps_qs = Application.objects.filter(job__employer=employer_user)

    # Top-level metrics (all time)
    total_jobs = jobs_qs.count()
    active_jobs = jobs_qs.filter(is_active=True).count()
    jobs_filled = jobs_qs.filter(is_active=False).count()
    total_applications = apps_qs.count()

    # Time range filtering for chart datasets
    time_range = (request.GET.get('time_range') or '30d').lower()
    days_map = {'7d': 7, '30d': 30}
    if time_range in days_map:
        start_dt = tz_now() - timedelta(days=days_map[time_range])
        apps_filtered = apps_qs.filter(submitted_at__gte=start_dt)
    else:
        # 'all' → no additional filter
        apps_filtered = apps_qs

    # Applications per Job (bar): labels = job titles, data = counts
    per_job_counts = (
        apps_filtered.values('job__title')
        .annotate(c=Count('id'))
        .order_by('-c', 'job__title')
    )
    applications_per_job = {
        'labels': [row['job__title'] for row in per_job_counts],
        'data': [row['c'] for row in per_job_counts],
    }

    # Applications over time (line): group by date
    over_time = (
        apps_filtered
        .annotate(day=TruncDate('submitted_at'))
        .values('day')
        .annotate(c=Count('id'))
        .order_by('day')
    )
    applications_over_time = {
        'labels': [row['day'].isoformat() if row['day'] else '' for row in over_time],
        'data': [row['c'] for row in over_time],
    }

    # Status breakdown (pie)
    status_rows = (
        apps_filtered.values('status')
        .annotate(c=Count('id'))
        .order_by('status')
    )
    status_breakdown = {
        'labels': [row['status'] for row in status_rows],
        'data': [row['c'] for row in status_rows],
    }

    # AJAX: return datasets only
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'time_range': time_range,
            'applications_per_job': applications_per_job,
            'applications_over_time': applications_over_time,
            'status_breakdown': status_breakdown,
        })

    # Non-AJAX: render full page
    # Provide jobs for recent activity table
    jobs = jobs_qs.order_by('-updated_at' if hasattr(Job, 'updated_at') else '-created_at')

    # Initial bootstrap datasets (JSON-friendly dicts)
    chart_bootstrap = {
        'time_range': time_range,
        'applications_per_job': applications_per_job,
        'applications_over_time': applications_over_time,
        'status_breakdown': status_breakdown,
    }

    return render(request, 'employers/analytics.html', {
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'jobs_filled': jobs_filled,
        'total_applications': total_applications,
        'time_range': time_range,
        'chart_bootstrap': chart_bootstrap,
        'jobs': jobs,
    })


# =========================
# Employer: Schedule Interview (create with conflicts)
# =========================
@login_required
@require_POST
def schedule_interview(request):
    from .models import Interview
    job_id = request.POST.get('job_id')
    cand_username = (request.POST.get('candidate_username') or '').strip()
    dt_raw = request.POST.get('datetime')
    notes = (request.POST.get('notes') or '').strip()

    if not job_id or not cand_username or not dt_raw:
        messages.error(request, 'Please fill Job, Candidate, and Date/Time.')
        return redirect('dashboard:employer')

    job = Job.objects.filter(id=job_id, employer=request.user).first()
    if not job:
        messages.error(request, 'Invalid job selection.')
        return redirect('dashboard:employer')

    from django.contrib.auth.models import User
    candidate = User.objects.filter(username=cand_username).first()
    if not candidate:
        messages.error(request, 'Candidate not found.')
        return redirect('dashboard:employer')
    if not Application.objects.filter(job__employer=request.user, applicant=candidate).exists():
        messages.error(request, 'Candidate has not applied to your jobs.')
        return redirect('dashboard:employer')

    from datetime import datetime, timedelta
    try:
        naive = datetime.fromisoformat(dt_raw)
    except Exception:
        messages.error(request, 'Invalid date/time format.')
        return redirect('dashboard:employer')
    try:
        scheduled_dt = timezone.make_aware(naive)
    except Exception:
        scheduled_dt = naive
    if scheduled_dt < timezone.now():
        messages.error(request, 'Please choose a future date/time.')
        return redirect('dashboard:employer')

    win_start = scheduled_dt - timedelta(minutes=30)
    win_end = scheduled_dt + timedelta(minutes=30)
    overlap = Interview.objects.filter(
        candidate=candidate,
        status__in=[Interview.STATUS_PLANNED, Interview.STATUS_RESCHEDULED],
        scheduled_at__gte=win_start,
        scheduled_at__lte=win_end,
    ).exists()
    if overlap:
        messages.error(request, 'Candidate has another interview around that time.')
        return redirect('dashboard:employer')

    interview = Interview.objects.create(
        job=job,
        employer=request.user,
        candidate=candidate,
        scheduled_at=scheduled_dt,
        notes=notes,
        status=Interview.STATUS_PLANNED,
    )
    # Create user-scoped notifications (no broadcast)
    try:
        from .models import Notification as _N
        from django.urls import reverse
        # Candidate notification
        _N.objects.create(
            user=candidate,
            title="Interview Scheduled",
            message=f"Your interview for '{job.title}' has been scheduled on {scheduled_dt.strftime('%b %d, %Y %I:%M %p')}",
            url=reverse('dashboard:user'),
            job=job,
        )
        # Employer confirmation
        _N.objects.create(
            user=request.user,
            title="Interview Scheduled",
            message=f"Interview scheduled with {candidate.get_full_name() or candidate.username} for '{job.title}' on {scheduled_dt.strftime('%b %d, %Y %I:%M %p')}",
            url=reverse('dashboard:employer'),
            job=job,
        )
    except Exception:
        pass
    # Email both parties
    try:
        from django.core.mail import send_mail
        when_str = scheduled_dt.strftime('%b %d, %Y %I:%M %p')
        send_mail(
            subject=f"Interview Scheduled: {job.title}",
            message=f"Your interview has been scheduled on {when_str}.",
            from_email=None,
            recipient_list=[candidate.email],
            fail_silently=True,
        )
        send_mail(
            subject=f"Interview Scheduled (Employer): {job.title}",
            message=f"You scheduled an interview with {candidate.get_full_name() or candidate.username} on {when_str}.",
            from_email=None,
            recipient_list=[request.user.email],
            fail_silently=True,
        )
    except Exception:
        pass

    messages.success(request, 'Interview scheduled successfully.')
    return redirect('dashboard:employer')


# =========================
# Employer: Candidate autocomplete (applicants only)
# =========================
@login_required
def employer_candidates(request):
    q = (request.GET.get('q') or '').strip()
    from django.contrib.auth.models import User
    qs = User.objects.filter(applications__job__employer=request.user).distinct()
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    results = list(qs.order_by('username')[:10].values('username', 'first_name', 'last_name'))
    payload = [{
        'username': r['username'],
        'name': ((r.get('first_name') or '') + (' ' + (r.get('last_name') or '') if r.get('last_name') else '')).strip() or r['username']
    } for r in results]
    return JsonResponse({'ok': True, 'results': payload})


# (Removed duplicate placeholder schedule_interview; functional version above remains)


# =========================
# Employer: Toggle job active
# =========================
@login_required
@require_POST
def employer_job_toggle(request, job_id: int):
    """Allow an employer to toggle their own job's active flag."""
    job = Job.objects.filter(id=job_id).first()
    if not job:
        messages.error(request, 'Job not found.')
        return redirect('dashboard:employer')
    if job.employer != request.user:
        messages.error(request, 'You do not have permission to modify this job.')
        return redirect('dashboard:employer')
    job.is_active = not job.is_active
    job.save(update_fields=['is_active'])
    # User-scoped notification (no broadcasts)
    try:
        from .models import Notification as _N
        _N.objects.create(
            user=request.user,
            title="Job Status Updated",
            message=(f"Activated: {job.title}" if job.is_active else f"Deactivated: {job.title}"),
            job=job,
        )
    except Exception:
        pass
    messages.success(request, f"{'Activated' if job.is_active else 'Deactivated'}: {job.title}")
    return redirect('dashboard:employer')


# =========================
# Employer: Reschedule / Cancel endpoints
# =========================
@login_required
@require_POST
def reschedule_interview(request):
    from .models import Interview
    interview_id = request.POST.get('interview_id')
    dt_raw = request.POST.get('datetime')
    if not interview_id or not dt_raw:
        messages.error(request, 'Missing interview or new date/time.')
        return redirect('dashboard:employer')

    interview = Interview.objects.select_related('job', 'candidate').filter(id=interview_id, employer=request.user).first()
    if not interview:
        messages.error(request, 'Interview not found or not yours.')
        return redirect('dashboard:employer')

    from datetime import datetime
    try:
        naive = datetime.fromisoformat(dt_raw)
        scheduled_dt = timezone.make_aware(naive)
    except Exception:
        messages.error(request, 'Invalid date/time.')
        return redirect('dashboard:employer')

    if scheduled_dt < timezone.now():
        messages.error(request, 'Choose a future date/time.')
        return redirect('dashboard:employer')

    interview.status = Interview.STATUS_RESCHEDULED
    interview.scheduled_at = scheduled_dt
    interview.save(update_fields=['status', 'scheduled_at', 'updated_at'])

    # Email both parties
    try:
        from django.core.mail import send_mail
        when_str = scheduled_dt.strftime('%b %d, %Y %I:%M %p')
        send_mail(
            subject=f"Interview Rescheduled: {interview.job.title}",
            message=f"Your interview was rescheduled to {when_str}.",
            from_email=None,
            recipient_list=[interview.candidate.email],
            fail_silently=True,
        )
        send_mail(
            subject=f"Interview Rescheduled (Employer): {interview.job.title}",
            message=f"Rescheduled with {interview.candidate.get_full_name() or interview.candidate.username} to {when_str}.",
            from_email=None,
            recipient_list=[request.user.email],
            fail_silently=True,
        )
    except Exception:
        pass

    messages.success(request, 'Interview rescheduled.')
    return redirect('dashboard:employer')


@login_required
@require_POST
def cancel_interview(request):
    from .models import Interview
    interview_id = request.POST.get('interview_id')
    if not interview_id:
        messages.error(request, 'Missing interview.')
        return redirect('dashboard:employer')

    interview = Interview.objects.select_related('job', 'candidate').filter(id=interview_id, employer=request.user).first()
    if not interview:
        messages.error(request, 'Interview not found or not yours.')
        return redirect('dashboard:employer')

    interview.status = Interview.STATUS_CANCELED
    interview.save(update_fields=['status', 'updated_at'])

    # Email both parties
    try:
        from django.core.mail import send_mail
        when_str = interview.scheduled_at.strftime('%b %d, %Y %I:%M %p')
        send_mail(
            subject=f"Interview Canceled: {interview.job.title}",
            message=f"Your interview on {when_str} was canceled.",
            from_email=None,
            recipient_list=[interview.candidate.email],
            fail_silently=True,
        )
        send_mail(
            subject=f"Interview Canceled (Employer): {interview.job.title}",
            message=f"Canceled interview with {interview.candidate.get_full_name() or interview.candidate.username} that was on {when_str}.",
            from_email=None,
            recipient_list=[request.user.email],
            fail_silently=True,
        )
    except Exception:
        pass

    messages.success(request, 'Interview canceled.')
    return redirect('dashboard:employer')


# =========================
# Employer: View applicants (modal content)
# =========================
@login_required
def job_applicants(request, job_id: int):
    """
    Render a small partial with applicants for the given job.
    Only the owning employer may view this list.
    """
    job = Job.objects.filter(id=job_id).first()
    if not job or job.employer != request.user:
        # Be conservative: do not leak existence
        return render(request, 'dashboard/partials/job_applicants_modal.html', {
            'job': None,
            'applications': [],
            'error': "Not authorized or job not found.",
        })

    apps = Application.objects.select_related('applicant').filter(job=job).order_by('-submitted_at')
    return render(request, 'dashboard/partials/job_applicants_modal.html', {
        'job': job,
        'applications': apps,
        'error': None,
    })


# =========================
# Admin Dashboard (custom)
# =========================
@login_required
@staff_member_required
def admin_dashboard(request):
    """
    Custom admin dashboard (separate from Django /admin/).
    Flesh out with KPIs as you go.
    """
    # Import models
    from django.contrib.auth.models import User
    from reroute_business.job_list.models import Job, Application
    from reroute_business.resumes.models import Resume
    from reroute_business.profiles.models import UserProfile, EmployerProfile

    # Stats
    user_count = User.objects.count()
    # Count employers by EmployerProfile presence (authoritative when table exists)
    try:
        employer_count = EmployerProfile.objects.count()
    except Exception:
        # Fallback: count users in Employer group(s) if EmployerProfile table is missing
        try:
            employer_count = User.objects.filter(groups__name__in=["Employer", "Employers"]).distinct().count()
        except Exception:
            employer_count = 0
    job_count = Job.objects.count()
    application_count = Application.objects.count()
    resume_count = Resume.objects.count()

    # Last 30 days activity for charts
    today = now().date()
    last_30 = [today - timedelta(days=i) for i in range(29, -1, -1)]

    users_by_day = [
        User.objects.filter(date_joined__date=day).count() for day in last_30
    ]
    jobs_by_day = [
        Job.objects.filter(created_at__date=day).count() for day in last_30
    ]
    applications_by_day = [
        Application.objects.filter(submitted_at__date=day).count() for day in last_30
    ]
    # Approximate employers by day using User.date_joined for users who have an EmployerProfile
    try:
        from reroute_business.profiles.models import EmployerProfile
        employers_by_day = [
            EmployerProfile.objects.filter(user__date_joined__date=day).count() for day in last_30
        ]
    except Exception:
        employers_by_day = [0 for _ in last_30]

    # Recent activity (last 7 days)
    seven_days_ago = now() - timedelta(days=7)
    new_users = User.objects.filter(date_joined__gte=seven_days_ago).count()
    new_jobs = Job.objects.filter(created_at__gte=seven_days_ago).count()
    new_applications = Application.objects.filter(submitted_at__gte=seven_days_ago).count()

    trend_totals = {
        "users_30": sum(users_by_day),
        "jobs_30": sum(jobs_by_day),
        "applications_30": sum(applications_by_day),
        "employers_30": sum(employers_by_day),
    }

    # Flagged jobs queue (tolerate missing column prior to migration)
    try:
        # Force evaluation so we can catch DB errors when column is missing
        flagged_jobs = list(Job.objects.filter(is_flagged=True))
    except Exception:
        flagged_jobs = []

    # --- AnalyticsEvent summary (safe if table missing) ---
    analytics_summary = {
        "page_views_total": 0,
        "profile_completed_total": 0,
        "top_pages": [],  # list of {path, count}
        "last_7_days": {"page_views": 0, "profile_completed": 0},
    }
    try:
        from reroute_business.core.models import AnalyticsEvent
        from django.db.models import Count

        seven_days_ago = now() - timedelta(days=7)
        qs = AnalyticsEvent.objects.all()
        analytics_summary["page_views_total"] = qs.filter(event_type="page_view").count()
        analytics_summary["profile_completed_total"] = qs.filter(event_type="profile_completed").count()
        analytics_summary["last_7_days"]["page_views"] = qs.filter(event_type="page_view", created_at__gte=seven_days_ago).count()
        analytics_summary["last_7_days"]["profile_completed"] = qs.filter(event_type="profile_completed", created_at__gte=seven_days_ago).count()
        top = (
            qs.filter(event_type="page_view")
              .values("path")
              .annotate(c=Count("id"))
              .order_by("-c")[:20]
        )
        analytics_summary["top_pages"] = [{"path": t["path"] or "/", "count": t["c"]} for t in top]
    except Exception:
        pass

    active_users_7 = User.objects.filter(last_login__gte=seven_days_ago).count()
    try:
        employers_pending = EmployerProfile.objects.filter(verified=False).count()
    except Exception:
        employers_pending = 0

    jobs_pending_review = len(flagged_jobs)
    open_flags = len(flagged_jobs)
    site_views_7 = analytics_summary["last_7_days"]["page_views"]

    review_queue = []
    for job in flagged_jobs[:6]:
        review_queue.append({
            "title": job.title,
            "reason": job.flagged_reason or "Job listing flagged for review",
            "timestamp": job.created_at,
            "severity": "high",
            "url": reverse("admin_portal:job_detail", args=[job.id]),
            "kind": "job",
        })
    try:
        pending_employers = EmployerProfile.objects.filter(verified=False).select_related("user")[:6]
        for employer in pending_employers:
            review_queue.append({
                "title": employer.company_name,
                "reason": "Pending employer approval",
                "timestamp": employer.user.date_joined,
                "severity": "medium",
                "url": reverse("admin_portal:employer_detail", args=[employer.id]),
                "kind": "employer",
            })
    except Exception:
        pass
    review_queue = sorted(review_queue, key=lambda item: item["timestamp"] or now(), reverse=True)[:8]

    activity_items = []
    for app in Application.objects.select_related("job", "applicant").order_by("-submitted_at")[:6]:
        activity_items.append({
            "title": f"{app.applicant.get_full_name() or app.applicant.username} applied",
            "detail": f"{app.job.title}",
            "timestamp": app.submitted_at,
        })
    for job in Job.objects.select_related("employer").order_by("-created_at")[:4]:
        activity_items.append({
            "title": f"{job.title}",
            "detail": f"Posted by {job.employer.get_full_name() or job.employer.username}",
            "timestamp": job.created_at,
        })
    activity_items = sorted(activity_items, key=lambda item: item["timestamp"] or now(), reverse=True)[:8]

    context = {
        "user_count": user_count,
        "employer_count": employer_count,
        "job_count": job_count,
        "application_count": application_count,
        "resume_count": resume_count,
        "dates": [d.strftime("%b %d") for d in last_30],
        "users_by_day": users_by_day,
        "jobs_by_day": jobs_by_day,
        "applications_by_day": applications_by_day,
        "employers_by_day": employers_by_day,
        "flagged_jobs": flagged_jobs,
        "new_users": new_users,
        "new_jobs": new_jobs,
        "new_applications": new_applications,
        "trend_totals": trend_totals,
        "analytics_summary": analytics_summary,
        "active_users_7": active_users_7,
        "jobs_pending_review": jobs_pending_review,
        "employers_pending": employers_pending,
        "open_flags": open_flags,
        "site_views_7": site_views_7,
        "review_queue": review_queue,
        "activity_items": activity_items,
        "reports_flags_count": _reports_flags_count(),
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
@staff_member_required
def admin_analytics_events(request):
    """
    Admin analytics: visualize AnalyticsEvent data.
    - Pie chart of page views by path (percent share)
    - Tiles for totals (page views, unique visitors, profiles completed, resumes created)
    - Top referrers
    """
    from reroute_business.core.models import AnalyticsEvent
    from django.db.models import Count

    try:
        days = int(request.GET.get('days') or 30)
    except ValueError:
        days = 30
    start_ts = now() - timedelta(days=days)

    events = AnalyticsEvent.objects.filter(created_at__gte=start_ts)

    # Page views by path (top N, rest grouped as Other)
    page_views_qs = (
        events.filter(event_type='page_view')
              .values('path')
              .annotate(count=Count('id'))
              .order_by('-count')
    )
    page_views_total = sum(r['count'] for r in page_views_qs)

    TOP_N = 7
    top_rows = list(page_views_qs[:TOP_N])
    other_count = page_views_total - sum(r['count'] for r in top_rows)

    pie_labels = [(r['path'] or '/') for r in top_rows]
    pie_counts = [r['count'] for r in top_rows]
    if other_count > 0:
        pie_labels.append('Other')
        pie_counts.append(other_count)

    # Unique visitors approximation by IP in metadata
    try:
        unique_visitors = (
            events.filter(event_type='page_view')
                  .exclude(metadata__ip__isnull=True)
                  .exclude(metadata__ip='')
                  .values('metadata__ip')
                  .distinct()
                  .count()
        )
    except Exception:
        unique_visitors = 0

    # Profiles completed
    profiles_completed = events.filter(event_type='profile_completed').count()

    # Resumes created (prefer event, fallback to model date)
    try:
        resumes_created = events.filter(event_type='resume_created').count()
        if resumes_created == 0:
            from reroute_business.resumes.models import Resume
            resumes_created = Resume.objects.filter(created_at__gte=start_ts).count()
    except Exception:
        resumes_created = 0

    # Top referrers
    try:
        ref_qs = (
            events.filter(event_type='page_view')
                  .exclude(metadata__referer__isnull=True)
                  .exclude(metadata__referer='')
                  .values('metadata__referer')
                  .annotate(count=Count('id'))
                  .order_by('-count')[:10]
        )
        top_referrers = [{'referer': r['metadata__referer'], 'count': r['count']} for r in ref_qs]
    except Exception:
        top_referrers = []

    context = {
        'days': days,
        'pie_labels': pie_labels,
        'pie_counts': pie_counts,
        # Time-series: views per day
        'views_by_day_labels': [],
        'views_by_day_counts': [],
        # Stacked: authed vs anon per day
        'views_by_day_authed': [],
        'views_by_day_anon': [],
        'page_views_total': page_views_total,
        'unique_visitors': unique_visitors,
        'profiles_completed': profiles_completed,
        'resumes_created': resumes_created,
        'top_pages': list(page_views_qs[:10]),
        'top_referrers': top_referrers,
        'reports_flags_count': _reports_flags_count(),
    }
    # Build daily series for the selected window
    try:
        from django.db.models.functions import TruncDate
        series_qs = (
            events.filter(event_type='page_view')
                  .annotate(day=TruncDate('created_at'))
                  .values('day')
                  .annotate(count=Count('id'))
                  .order_by('day')
        )
        # Full day list to fill zeros
        days_list = [ (now() - timedelta(days=i)).date() for i in range(days-1, -1, -1) ]
        by_day_map = { r['day']: r['count'] for r in series_qs }
        context['views_by_day_labels'] = [d.strftime('%b %d') for d in days_list]
        context['views_by_day_counts'] = [ by_day_map.get(d, 0) for d in days_list ]

        # Stacked: authed vs anon per day
        authed_qs = (
            events.filter(event_type='page_view').exclude(user__isnull=True)
                  .annotate(day=TruncDate('created_at'))
                  .values('day').annotate(count=Count('id'))
        )
        anon_qs = (
            events.filter(event_type='page_view', user__isnull=True)
                  .annotate(day=TruncDate('created_at'))
                  .values('day').annotate(count=Count('id'))
        )
        authed_map = { r['day']: r['count'] for r in authed_qs }
        anon_map = { r['day']: r['count'] for r in anon_qs }
        context['views_by_day_authed'] = [ authed_map.get(d, 0) for d in days_list ]
        context['views_by_day_anon'] = [ anon_map.get(d, 0) for d in days_list ]
    except Exception:
        pass

    return render(request, 'dashboard/admin_analytics_events.html', context)


# =========================
# In-site Admin: Manage Jobs
# =========================
@login_required
@staff_member_required
def admin_jobs_manage(request):
    q = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or '').strip().lower()  # '', 'active', 'inactive', 'flagged'

    jobs = Job.objects.select_related('employer').all().order_by('-created_at')
    if q:
        jobs = jobs.filter(Q(title__icontains=q) | Q(employer__username__icontains=q) | Q(location__icontains=q))
    if status == 'active':
        jobs = jobs.filter(is_active=True)
    elif status == 'inactive':
        jobs = jobs.filter(is_active=False)
    elif status == 'flagged':
        try:
            jobs = jobs.filter(is_flagged=True)
        except Exception:
            jobs = jobs.none()

    return render(request, 'dashboard/admin_jobs_manage.html', {
        'jobs': jobs,
        'q': q,
        'status': status,
        'reports_flags_count': _reports_flags_count(),
    })


@login_required
@staff_member_required
@require_POST
def admin_job_toggle_active(request, job_id: int):
    job = Job.objects.filter(id=job_id).first()
    if not job:
        messages.error(request, 'Job not found.')
        return redirect('dashboard:admin_jobs_manage')
    job.is_active = not job.is_active
    job.save(update_fields=['is_active'])
    messages.success(request, f"{'Activated' if job.is_active else 'Deactivated'}: {job.title}")
    return redirect('dashboard:admin_jobs_manage')


# =========================
# In-site Admin: Manage Applications
# =========================
@login_required
@staff_member_required
def admin_applications_manage(request):
    status = (request.GET.get('status') or '').strip()
    q = (request.GET.get('q') or '').strip()
    apps = Application.objects.select_related('job', 'applicant').all().order_by('-submitted_at')
    if status:
        apps = apps.filter(status=status)
    if q:
        apps = apps.filter(Q(job__title__icontains=q) | Q(applicant__username__icontains=q))

    # Use field metadata for authoritative choices
    try:
        status_choices = Application._meta.get_field('status').choices
    except Exception:
        status_choices = getattr(Application, 'STATUS_CHOICES', [])

    return render(request, 'dashboard/admin_applications_manage.html', {
        'applications': apps,
        'q': q,
        'status': status,
        'status_choices': status_choices,
        'reports_flags_count': _reports_flags_count(),
    })


@login_required
@staff_member_required
@require_POST
def admin_application_update_status(request, app_id: int):
    app = Application.objects.select_related('job').filter(id=app_id).first()
    if not app:
        messages.error(request, 'Application not found.')
        return redirect('dashboard:admin_applications_manage')
    new_status = (request.POST.get('status') or '').strip()
    valid = {s for s, _ in getattr(Application, 'STATUS_CHOICES', [])}
    if new_status not in valid:
        messages.error(request, 'Invalid status.')
        return redirect('dashboard:admin_applications_manage')
    app.status = new_status
    app.save(update_fields=['status'])
    messages.success(request, f"Updated status to {new_status} for {app.job.title}")
    return redirect('dashboard:admin_applications_manage')


@login_required
@staff_member_required
@require_POST
def approve_flagged_job(request, job_id: int):
    from reroute_business.job_list.models import Job
    job = Job.objects.filter(id=job_id).first()
    if not job:
        messages.error(request, "Job not found.")
        return redirect('dashboard:admin')

    job.is_flagged = False
    job.flagged_reason = None
    job.is_active = True
    job.save(update_fields=['is_flagged', 'flagged_reason', 'is_active'])

    messages.success(request, f"Approved and unflagged: {job.title}")
    return redirect('dashboard:admin')


@login_required
@staff_member_required
@require_POST
def remove_flagged_job(request, job_id: int):
    from reroute_business.job_list.models import Job
    job = Job.objects.filter(id=job_id).first()
    if not job:
        messages.error(request, "Job not found.")
        return redirect('dashboard:admin')

    # Soft-remove: deactivate the job and clear flag
    job.is_active = False
    job.is_flagged = False
    if not job.flagged_reason:
        job.flagged_reason = "Removed by admin"
    job.save(update_fields=['is_active', 'is_flagged', 'flagged_reason'])

    messages.success(request, f"Removed (deactivated): {job.title}")
    return redirect('dashboard:admin')


# =========================
# Profile Settings (Private)
# =========================
def _allowed_profile_gradients():
    return {key for key, _label in PROFILE_GRADIENT_CHOICES}


def _validate_image_upload(image_file, max_bytes):
    if max_bytes and image_file.size > max_bytes:
        return "Image exceeds the maximum upload size."
    try:
        img = Image.open(image_file)
        img.verify()
        if img.format and img.format.lower() not in {"jpeg", "jpg", "png", "gif", "webp"}:
            return "Unsupported image format. Use JPEG, PNG, GIF, or WebP."
    except UnidentifiedImageError:
        return "Invalid image file. Please upload a real image."
    return None


def _touch_profile_progress(profile):
    try:
        profile.update_onboarding_flags()
        profile.save(update_fields=["onboarding_step", "onboarding_completed", "early_access_priority"])
    except Exception:
        pass


@login_required
@require_POST
def profile_details_update(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    first = (request.POST.get("first_name") or "").strip()
    last = (request.POST.get("last_name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    gender = (request.POST.get("gender") or "").strip()

    errors = {}
    if not first:
        errors["first_name"] = "First name is required."
    if not last:
        errors["last_name"] = "Last name is required."

    allowed_genders = {value for value, _label in GENDER_CHOICES}
    if gender and gender not in allowed_genders:
        errors["gender"] = "Please choose a valid option."

    allow_email_change = bool(getattr(settings, "ALLOW_PROFILE_EMAIL_CHANGE", True))
    if email and allow_email_change:
        from django.contrib.auth.models import User
        if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
            errors["email"] = "That email is already in use."
    elif email and not allow_email_change:
        errors["email"] = "Email changes are not allowed right now."

    if errors:
        return _json_err(errors, status=400)

    if first != request.user.first_name or last != request.user.last_name:
        request.user.first_name = first
        request.user.last_name = last
        request.user.save(update_fields=["first_name", "last_name"])

    if allow_email_change and email and email != request.user.email:
        request.user.email = email
        request.user.save(update_fields=["email"])

    profile.firstname = first
    profile.lastname = last
    profile.phone_number = phone
    profile.gender = gender
    profile.save(update_fields=["firstname", "lastname", "phone_number", "gender"])
    _touch_profile_progress(profile)

    return _json_ok({
        "first_name": first,
        "last_name": last,
        "email": request.user.email,
        "phone": phone,
        "gender": gender,
    })


@login_required
@require_POST
def profile_avatar_upload(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    image_file = request.FILES.get("avatar")
    if not image_file:
        return _json_err({"avatar": "Please choose an image to upload."}, status=400)

    max_bytes = getattr(settings, "PROFILE_IMAGE_MAX_BYTES", None)
    if not max_bytes:
        max_bytes = getattr(settings, "FILE_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024)
    error = _validate_image_upload(image_file, max_bytes)
    if error:
        return _json_err({"avatar": error}, status=400)

    profile.profile_picture = image_file
    profile.save(update_fields=["profile_picture"])
    _touch_profile_progress(profile)
    return _json_ok({"avatar_url": profile.profile_picture.url})


@login_required
@require_POST
def profile_avatar_delete(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.profile_picture:
        profile.profile_picture.delete(save=False)
        profile.profile_picture = None
        profile.save(update_fields=["profile_picture"])
    _touch_profile_progress(profile)
    return _json_ok({"avatar_url": ""})


@login_required
@require_POST
def profile_background_set(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    gradient = (request.POST.get("gradient") or "").strip()
    allowed = _allowed_profile_gradients()
    if gradient not in allowed:
        return _json_err({"gradient": "Please select a valid background."}, status=400)
    profile.background_gradient = gradient
    profile.save(update_fields=["background_gradient"])
    return _json_ok({"gradient": gradient})


@login_required
@require_POST
def profile_bio_update(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    bio = (request.POST.get("bio") or "").strip()
    max_len = int(getattr(settings, "PROFILE_BIO_MAX_CHARS", 600))
    if len(bio) > max_len:
        return _json_err({"bio": f"Bio must be {max_len} characters or fewer."}, status=400)
    profile.bio = bio
    profile.save(update_fields=["bio"])
    _touch_profile_progress(profile)
    return _json_ok({"bio": bio})


@login_required
@require_POST
def profile_experience_add(request):
    resume = Resume.objects.filter(user=request.user).order_by("-created_at").first()
    if not resume:
        resume = Resume.objects.create(user=request.user)

    job_title = (request.POST.get("job_title") or "").strip()
    company = (request.POST.get("company") or "").strip()
    start_date = (request.POST.get("start_date") or "").strip()
    end_date = (request.POST.get("end_date") or "").strip()
    currently_work_here = (request.POST.get("currently_work_here") or "") == "on"
    description = (request.POST.get("description") or "").strip()

    errors = {}
    if not job_title:
        errors["job_title"] = "Job title is required."
    if not company:
        errors["company"] = "Company is required."
    if not start_date:
        errors["start_date"] = "Start date is required."

    if errors:
        return _json_err(errors, status=400)

    from django.utils.dateparse import parse_date
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date) if end_date else None
    if not start_dt:
        return _json_err({"start_date": "Start date is invalid."}, status=400)
    if end_date and not end_dt:
        return _json_err({"end_date": "End date is invalid."}, status=400)
    if currently_work_here:
        end_dt = None

    experience = Experience.objects.create(
        resume=resume,
        job_title=job_title,
        company=company,
        start_date=start_dt,
        end_date=end_dt,
        currently_work_here=currently_work_here,
        description=description,
    )
    return _json_ok({
        "experience": {
            "id": experience.id,
            "job_title": experience.job_title,
            "company": experience.company,
            "start_date": experience.start_date.isoformat(),
            "end_date": experience.end_date.isoformat() if experience.end_date else "",
            "currently_work_here": experience.currently_work_here,
            "description": experience.description or "",
        }
    })


@login_required
@require_POST
def profile_experience_delete(request, experience_id):
    experience = get_object_or_404(Experience, id=experience_id, resume__user=request.user)
    experience.delete()
    return _json_ok({"deleted": experience_id})


@login_required
@require_POST
def profile_skill_add(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    name = (request.POST.get("skill") or "").strip()
    if not name:
        return _json_err({"skill": "Enter a skill to add."}, status=400)
    if len(name) > 40:
        return _json_err({"skill": "Skill must be 40 characters or fewer."}, status=400)
    if profile.skills.filter(name__iexact=name).exists():
        skills = [{"id": s.id, "name": s.name} for s in profile.skills.all().order_by("name")]
        return _json_ok({"skills": skills})

    existing = Skill.objects.filter(name__iexact=name).first()
    if not existing:
        existing = Skill.objects.create(name=name)
    profile.skills.add(existing)
    skills = [{"id": s.id, "name": s.name} for s in profile.skills.all().order_by("name")]
    return _json_ok({"skills": skills})


@login_required
@require_POST
def profile_skill_delete(request, skill_id):
    profile = get_object_or_404(UserProfile, user=request.user)
    skill = get_object_or_404(Skill, id=skill_id)
    profile.skills.remove(skill)
    skills = [{"id": s.id, "name": s.name} for s in profile.skills.all().order_by("name")]
    return _json_ok({"skills": skills})


@login_required
@require_POST
def profile_language_add(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    name = (request.POST.get("language") or "").strip()
    if not name:
        return _json_err({"language": "Enter a language to add."}, status=400)
    if len(name) > 40:
        return _json_err({"language": "Language must be 40 characters or fewer."}, status=400)
    if profile.languages.filter(name__iexact=name).exists():
        languages = [{"id": l.id, "name": l.name} for l in profile.languages.all().order_by("name")]
        return _json_ok({"languages": languages})

    existing = Language.objects.filter(name__iexact=name).first()
    if not existing:
        existing = Language.objects.create(name=name)
    profile.languages.add(existing)
    languages = [{"id": l.id, "name": l.name} for l in profile.languages.all().order_by("name")]
    return _json_ok({"languages": languages})


@login_required
@require_POST
def profile_language_delete(request, language_id):
    profile = get_object_or_404(UserProfile, user=request.user)
    language = get_object_or_404(Language, id=language_id)
    profile.languages.remove(language)
    languages = [{"id": l.id, "name": l.name} for l in profile.languages.all().order_by("name")]
    return _json_ok({"languages": languages})
