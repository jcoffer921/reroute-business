# job_list/user/views.py

from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse, NoReverseMatch
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.mail import send_mail
from core.utils.analytics import track_event
from django.http import JsonResponse, HttpResponse

from job_list.models import Job, Application, SavedJob
from job_list.utils.geo import is_within_radius  # expects (origin_zip, target_zip, radius_mi)
from resumes.models import Resume
from django.contrib.auth.models import User

from core.models import Skill


import logging
logger = logging.getLogger(__name__)  # Set up logger for this module

# ---------- Browse jobs with real filters ----------
def opportunities_view(request):
    """
    Filters:
      - q: keyword search in title/description/requirements
      - type=full_time|part_time|... (repeats allowed)
      - zip=19104 (optional) + radius=25 (miles, optional; default 25)
    """
    jobs_qs = Job.objects.filter(is_active=True).select_related('employer').prefetch_related('skills_required')

    # --- Keyword search across key fields ---
    q = (request.GET.get('q') or "").strip()
    if q:
        tokens = [t for t in q.split() if t]
        for t in tokens:
            jobs_qs = jobs_qs.filter(
                Q(title__icontains=t) |
                Q(description__icontains=t) |
                Q(requirements__icontains=t)
            )

    # --- Filter by employer username (optional) ---
    employer_username = (request.GET.get('employer') or '').strip()
    if employer_username:
        jobs_qs = jobs_qs.filter(employer__username=employer_username)

    # --- Job type filter (use the job_type field, not tags regex) ---
    job_types = request.GET.getlist('type')
    # Track normalized types for template checked-state
    normalized_types = []
    if job_types:
        # Normalize display labels like "Full-Time" → internal values "full_time"
        for t in job_types:
            t = (t or "").strip()
            # Accept both internal values and labels
            tv = t.lower().replace('-', '_').replace(' ', '_')
            # Map common label forms to internal constants
            if tv in {"full_time", "part_time", "contract", "internship", "temporary"}:
                normalized_types.append(tv)
        if normalized_types:
            jobs_qs = jobs_qs.filter(job_type__in=normalized_types)

    # --- Optional radius filter by ZIP ---
    # Support preset radios without conflicting with the free-text ZIP input
    preset_zip = (request.GET.get('preset_zip') or "").strip()
    user_zip = preset_zip or (request.GET.get('zip') or "").strip()
    radius = request.GET.get('radius')
    try:
        radius = int(radius) if radius not in (None, "") else 25
    except ValueError:
        radius = 25

    # If using distance, filter in Python; otherwise keep queryset for DB ordering
    if user_zip:
        jobs_in_radius = []
        for job in jobs_qs:
            if job.zip_code and is_within_radius(user_zip, job.zip_code, radius):
                jobs_in_radius.append(job)
        jobs = jobs_in_radius
    else:
        jobs = list(jobs_qs.order_by('-created_at'))

    # --- Saved flags for the current user ---
    saved_job_ids = set()
    if request.user.is_authenticated:
        saved_job_ids = set(
            SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True)
        )

    context = {
        'jobs': jobs,
        'saved_job_ids': saved_job_ids,
        # expose current filters for template state
        'q': q,
        'user_zip': user_zip,
        'radius': radius,
        'selected_job_types': normalized_types,
        'selected_preset_zip': preset_zip,
        'selected_employer': employer_username,
    }

    # AJAX: return only the jobs list HTML for in-page updates
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render(request, 'job_list/user/_jobs_list.html', context=context).content
        return HttpResponse(html, content_type='text/html')

    return render(request, 'job_list/user/opportunities.html', context)

@require_POST
@login_required
def toggle_saved_job(request):
    job_id = request.POST.get('job_id')
    job = Job.objects.filter(id=job_id).first()

    if not job:
        logger.warning(f"[❌] Job ID {job_id} not found. User: {request.user}")
        return JsonResponse({'error': 'Job not found'}, status=404)

    logger.info(f"[🔁] Toggle save called for job {job_id} by user {request.user}")

    # Try to get or create the saved job entry
    saved, created = SavedJob.objects.get_or_create(user=request.user, job=job)

    if not created:
        saved.delete()
        logger.info(f"[🗑️] Job {job_id} unsaved by user {request.user}")
        return JsonResponse({'status': 'unsaved'})

    logger.info(f"[✅] Job {job_id} saved by user {request.user}")
    return JsonResponse({'status': 'saved'})

# View details for a specific job
def job_detail_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'job_list/user/job_detail.html', {'job': job})

# Apply to a job
@require_POST
@login_required
def apply_to_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    # Build a link to the applicant's public profile for the employer email/notifications.
    # Prefer namespaced route; fall back to global alias if project URLconf isn't namespaced.
    try:
        public_profile_path = reverse('profiles:public_profile', kwargs={'username': request.user.username})
    except NoReverseMatch:
        public_profile_path = reverse('public_profile', kwargs={'username': request.user.username})
    profile_url = request.build_absolute_uri(public_profile_path)

    # 🔒 Resume required
    resume = Resume.objects.filter(user=request.user).first()
    if not resume or not resume.file:
        messages.warning(request, "🚫 You need to upload a resume before applying. Please go to your dashboard and upload one.")
        return redirect('dashboard:my_dashboard')  # send to unified dashboard

    # ✅ Prevent duplicate applications
    if Application.objects.filter(applicant=request.user, job=job).exists():
        messages.warning(request, "You already applied.")
        return redirect('job_detail', job_id=job.id)

    # ✅ Create application
    application = Application.objects.create(applicant=request.user, job=job)
    # Analytics: application submitted
    try:
        track_event(event_type='application_submitted', user=request.user, metadata={'job_id': job.id, 'application_id': application.id})
    except Exception:
        pass

    # 🔔 In-app notification for employer
    try:
        from dashboard.models import Notification
        Notification.objects.create(
            user=job.employer,
            actor=request.user,
            verb="applied",
            message=f"{request.user.username} applied to your job: {job.title}",
            url=reverse('job_detail', kwargs={'job_id': job.id}),
            job=job,
            application=application,
        )
    except Exception:
        # Fail silently to avoid blocking application submit
        pass

    # 📧 Notify employer by email
    send_mail(
        subject=f"New Application: {job.title}",
        message=(
            f"{request.user.username} just applied to your job listing: {job.title}.\n\n"
            f"📄 View their profile: {profile_url}\n\n"
            "You can review their resume, background, and application status from your dashboard."
        ),
        from_email="noreply@reroutejobs.com",
        recipient_list=[job.employer.email],
        fail_silently=True,
    )

    messages.success(request, "Your application was submitted successfully!")
    return redirect('job_detail', job_id=job.id)

# ---------- Scored matching ----------
def match_jobs(request, seeker_id):
    """Delegate to the shared matching module and render the matches page."""
    from job_list.matching import match_jobs_for_user

    user = get_object_or_404(User, id=seeker_id)

    origin_zip = (request.GET.get('zip') or '').strip() or None
    radius = request.GET.get('radius')
    try:
        radius = int(radius) if radius not in (None, '') else 25
    except ValueError:
        radius = 25

    ordered_jobs = match_jobs_for_user(user, origin_zip=origin_zip, radius=radius)
    # Reuse the dashboard template that already renders a list of jobs
    return render(request, 'dashboard/matched_jobs.html', {
        'matches': ordered_jobs,
    })
