# dashboard/views.py

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q



# ===== Domain imports (align to your actual apps) =====
# Jobs live in job_list; bring Job, SavedJob, Application from there for consistency.
from job_list.models import Job, SavedJob, Application
from job_list.models import ArchivedJob
from django.db.utils import ProgrammingError
from job_list.matching import match_jobs_for_user

# Profiles & resumes
from profiles.models import UserProfile
from resumes.models import Education, Experience, Resume  # your resumes app owns these


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

    # Suggested jobs: only attempt if we detect skills
    skills_list = extract_resume_skills(resume)
    suggested_jobs = match_jobs_for_user(request.user)[:10] if skills_list else []

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
                suggested_cards.append({"job": job, "match": percent})
        else:
            suggested_cards = [{"job": j, "match": None} for j in (suggested_jobs or [])]
    except Exception:
        suggested_cards = [{"job": j, "match": None} for j in (suggested_jobs or [])]

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
        from core.models import AnalyticsEvent
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

    # Charts for seeker dashboard were removed per request.

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
        'notifications': notifications,
        'stats': {
            'applications_sent': applications_sent,
            'profile_views': profile_views,
            'matches_found': matches_found,
        },
        'upcoming_interviews': upcoming_interviews,
    })


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
    """Render matched jobs with optional ZIP/radius filters and overlap badges."""
    origin_zip = (request.GET.get('zip') or '').strip() or None
    try:
        radius = int(request.GET.get('radius') or 25)
    except ValueError:
        radius = 25

    matched_jobs = match_jobs_for_user(request.user, origin_zip=origin_zip, radius=radius)

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
        'selected_zip': origin_zip or '',
        'selected_radius': radius,
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
        from profiles.models import EmployerProfile
        EmployerProfile.objects.get_or_create(user=employer_user)
    except Exception:
        pass

    # Jobs "owned" by this employer, with simple sort control
    sort_by = (request.GET.get('sort_by') or 'newest').lower()
    order = '-created_at' if sort_by == 'newest' else 'created_at'
    jobs = Job.objects.filter(employer=employer_user).order_by(order)

    # Match candidates to this employer's jobs (top few per job)
    from job_list.matching import match_seekers_for_employer
    matched_seekers = match_seekers_for_employer(employer_user, limit_per_job=3)[:9]
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
    total_applications = Application.objects.filter(job__employer=employer_user).count()
    # Treat "filled" as inactive jobs for this dashboard
    jobs_filled = Job.objects.filter(employer=employer_user, is_active=False).count()

    analytics = {
        "jobs_posted": total_jobs,
        "active_jobs": active_jobs,
        "total_applicants": total_applications,
        "jobs_filled": jobs_filled,
    }

    # Employer verification flag (controls alert banner)
    employer_verified = False
    try:
        from profiles.models import EmployerProfile as _EP
        ep = _EP.objects.filter(user=employer_user).first()
        employer_verified = bool(getattr(ep, 'verified', False)) if ep else False
    except Exception:
        employer_verified = False

    return render(request, 'dashboard/employer_dashboard.html', {
        'jobs': jobs,
        'matched_seekers': matched_seekers,
        'notifications': notifications,
        'interviews': interviews,
        'analytics': analytics,
        # Expose individual variables for template clarity
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'total_applications': total_applications,
        'jobs_filled': jobs_filled,
        'sort_by': sort_by,
        'employer_verified': employer_verified,
    })


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
    from job_list.matching import match_seekers_for_employer
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
    from job_list.matching import match_seekers_for_employer
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
    from job_list.models import Job as _Job
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
        from profiles.models import UserProfile
        up = UserProfile.objects.filter(user=request.user).first()
        is_emp = bool(getattr(up, 'is_employer', False))
    except Exception:
        pass
    bcast = Q(user__isnull=True) & (
        Q(target_group=Notification.TARGET_ALL) |
        Q(target_group=Notification.TARGET_EMPLOYERS if is_emp else Notification.TARGET_SEEKERS)
    )
    notes = Notification.objects.filter(Q(user=request.user) | bcast).order_by('-created_at', '-id')
    return render(request, 'dashboard/notifications.html', { 'notifications': notes })


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
    from job_list.models import Job, Application
    from resumes.models import Resume
    from profiles.models import UserProfile, EmployerProfile

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
        from profiles.models import EmployerProfile
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
        from core.models import AnalyticsEvent
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
        "analytics_summary": analytics_summary,
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
    from core.models import AnalyticsEvent
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
            from resumes.models import Resume
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
    from job_list.models import Job
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
    from job_list.models import Job
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
