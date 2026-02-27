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

MAX_TAGS = 5

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

    def _default_form_data():
        return {
            "title": "",
            "description": "",
            "requirements": "",
            "location": "",
            "tags": "",
            "zip_code": "",
            "job_type": "full_time",
            "experience_level": "",
            "salary_type": "hour",
            "hourly_min": "",
            "hourly_max": "",
            "salary_min": "",
            "salary_max": "",
        }

    def _render_form(form_data=None, form_errors=None, status=200):
        context = {
            "employer_verified": employer_verified,
            "form_data": form_data or _default_form_data(),
            "form_errors": form_errors or {},
        }
        return render(request, 'job_list/employers/create_job.html', context, status=status)

    if not employer_profile or not employer_verified:
        messages.error(request, "Your employer account is pending verification. Please complete your profile and wait for approval before posting jobs.")
        return _render_form()

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
        cleaned_tags = []
        seen_tag_keys = set()
        for part in tags.split(","):
            tag = " ".join(part.split()).strip()
            if not tag:
                continue
            tag_key = tag.lower()
            if tag_key not in seen_tag_keys:
                seen_tag_keys.add(tag_key)
                cleaned_tags.append(tag)
        tags = ", ".join(cleaned_tags)

        form_data = {
            "title": title,
            "description": description,
            "requirements": requirements,
            "location": location,
            "tags": tags,
            "zip_code": zip_code,
            "job_type": job_type,
            "experience_level": experience_level,
            "salary_type": salary_type,
            "hourly_min": request.POST.get("hourly_min") or "",
            "hourly_max": request.POST.get("hourly_max") or "",
            "salary_min": request.POST.get("salary_min") or "",
            "salary_max": request.POST.get("salary_max") or "",
        }

        form_errors = {}
        if not title:
            form_errors["title"] = "Job title is required."
        if not description:
            form_errors["description"] = "Description is required."
        if not requirements:
            form_errors["requirements"] = "Requirements are required."
        if not location:
            form_errors["location"] = "Location is required."
        if zip_code and (not zip_code.isdigit() or len(zip_code) != 5):
            form_errors["zip_code"] = "ZIP code must be 5 digits."
        if len(cleaned_tags) > MAX_TAGS:
            form_errors["tags"] = f"You can add up to {MAX_TAGS} tags."

        if salary_type == 'hour' and hourly_min and hourly_max and hourly_min > hourly_max:
            form_errors["hourly_max"] = "Hourly max must be greater than or equal to hourly min."

        if salary_type == 'year' and salary_min and salary_max and salary_min > salary_max:
            form_errors["salary_max"] = "Yearly max must be greater than or equal to yearly min."

        if form_errors:
            messages.error(request, "Please fix the highlighted fields and try again.")
            return _render_form(form_data=form_data, form_errors=form_errors, status=400)

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

    return _render_form()
