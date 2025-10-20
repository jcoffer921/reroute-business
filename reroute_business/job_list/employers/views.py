# job_list/employers/views.py

from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from reroute_business.job_list.models import Job
from reroute_business.core.models import Skill
from reroute_business.core.utils.analytics import track_event
from reroute_business.profiles.models import EmployerProfile

# Show jobs posted by this employer
@login_required
def dashboard_view(request):
    """Restrict employer dashboard to employer accounts only."""
    is_employer = (
        request.user.groups.filter(name__in=["Employer", "Employers"]).exists()
        or hasattr(request.user, "employerprofile")
    )
    if not is_employer:
        # Be friendly: redirect to the unified dashboard instead of 403
        messages.error(request, "Access denied: Employers only.")
        return redirect('dashboard:my_dashboard')

    jobs = Job.objects.filter(employer=request.user)
    # Verification flag for gating UI affordances
    try:
        employer_verified = bool(getattr(request.user.employerprofile, 'verified', False))
    except Exception:
        employer_verified = False
    return render(request, 'dashboard/employer_dashboard.html', {
        'jobs': jobs,
        'employer_verified': employer_verified,
    })


@login_required
def create_job(request):
    """
    Create a job with guardrails:
      - Validates required fields
      - Validates pay ranges
      - Supports skills chips via skills[]=...
    """
    # Require verified employer profile before allowing job creation
    try:
        employer_profile = request.user.employerprofile
        employer_verified = bool(getattr(employer_profile, 'verified', False))
    except Exception:
        employer_profile = None
        employer_verified = False

    if not employer_profile or not employer_verified:
        messages.error(request, "Your employer account is pending verification. Please complete your profile and wait for approval before posting jobs.")
        return render(request, 'job_list/employers/create_job.html', {
            'employer_verified': employer_verified,
        })

    if request.method == 'POST':
        # Required
        title = (request.POST.get('title') or '').strip()
        description = (request.POST.get('description') or '').strip()
        requirements = (request.POST.get('requirements') or '').strip()
        location = (request.POST.get('location') or '').strip()

        # Optional
        tags = (request.POST.get('tags') or '').strip()
        zip_code = (request.POST.get('zip_code') or '').strip()
        job_type = request.POST.get('job_type') or 'full_time'
        experience_level = request.POST.get('experience_level') or ''
        salary_type = request.POST.get('salary_type') or 'hour'  # 'hour' or 'year'

        # Helpers
        def to_decimal(v):
            try: return Decimal(v) if v not in (None, '') else None
            except (InvalidOperation, TypeError): return None

        def to_int(v):
            try: return int(v) if v not in (None, '') else None
            except (ValueError, TypeError): return None

        hourly_min = to_decimal(request.POST.get('hourly_min'))
        hourly_max = to_decimal(request.POST.get('hourly_max'))
        salary_min = to_int(request.POST.get('salary_min'))   # "57" for $57k
        salary_max = to_int(request.POST.get('salary_max'))

        # Basic validation
        if not all([title, description, requirements, location]):
            messages.error(request, "Title, description, requirements and location are required.")
            return render(request, 'job_list/employers/create_job.html')

        if salary_type == 'hour' and hourly_min and hourly_max and hourly_min > hourly_max:
            messages.error(request, "Hourly min cannot be greater than hourly max.")
            return render(request, 'job_list/employers/create_job.html')

        if salary_type == 'year' and salary_min and salary_max and salary_min > salary_max:
            messages.error(request, "Salary min cannot be greater than salary max.")
            return render(request, 'job_list/employers/create_job.html')

        # Create job
        job = Job.objects.create(
            title=title,
            description=description,
            requirements=requirements,
            location=location,
            zip_code=zip_code,
            tags=tags,
            employer=request.user,
            job_type=job_type,
            experience_level=experience_level,
            salary_type=salary_type,
            hourly_min=hourly_min if salary_type == 'hour' else None,
            hourly_max=hourly_max if salary_type == 'hour' else None,
            salary_min=salary_min if salary_type == 'year' else None,
            salary_max=salary_max if salary_type == 'year' else None,
            currency='USD',
        )

        # OPTIONAL: skills chips support (form sends skills[]= carpentry, skills[]= forklift, ...)
        for raw in request.POST.getlist('skills[]'):
            name = " ".join(raw.strip().split()).lower()
            if not name: 
                continue
            skill, _ = Skill.objects.get_or_create(name=name)
            job.skills_required.add(skill)

        # Analytics: job created
        try:
            track_event(event_type='job_created', user=request.user, metadata={'job_id': job.id, 'title': job.title})
        except Exception:
            pass

        messages.success(request, "Job posted successfully.")
        return redirect('employer_dashboard')

    return render(request, 'job_list/employers/create_job.html', {
        'employer_verified': employer_verified,
    })
