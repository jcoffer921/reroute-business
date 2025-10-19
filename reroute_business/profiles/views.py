# profiles/views.py — slide-in friendly, JSON-first
from __future__ import annotations

import json
from datetime import datetime
try:
    from PIL import Image, UnidentifiedImageError
except Exception:
    Image = None
    class UnidentifiedImageError(Exception):
        pass
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.safestring import mark_safe

 

from .models import UserProfile, EmployerProfile, Subscription

# Optional integrations — guarded to avoid hard crashes if app not installed
try:
    from reroute_business.resumes.models import Resume
except Exception:
    Resume = None

try:
    from reroute_business.core.models import Skill
except Exception:
    Skill = None

# Curated, relatable skills for justice-impacted seekers
try:
    from reroute_business.core.constants import RELATABLE_SKILLS
except Exception:
    RELATABLE_SKILLS = []

# Optional constants (guarded)
try:
    from .constants import US_STATES, ETHNICITY_CHOICES
except Exception:
    US_STATES, ETHNICITY_CHOICES = [], []

# Optional: allauth email verification model
try:
    from allauth.account.models import EmailAddress
except Exception:
    EmailAddress = None


# ----------------------------- JSON helpers -----------------------------
def json_ok(updated=None, message=None, status=200):
    payload = {"ok": True}
    if updated is not None:
        payload["updated"] = updated
    if message:
        payload["message"] = message
    return JsonResponse(payload, status=status)

def json_err(errors, status=400):
    return JsonResponse({"ok": False, "errors": errors}, status=status)

def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

def is_employer(user) -> bool:
    """
    Public helper used by other apps (e.g., main.views).
    Checks if the user belongs to the Employer group(s).
    Kept defensive so it never crashes if groups aren't set up.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    try:
        return user.groups.filter(name__in=["Employer", "Employers"]).exists()
    except Exception:
        return False


# ----------------------------- Public profile ---------------------------
@login_required
def public_profile_view(request, username: str):
    # Only employers should view others' profiles (adjust logic as you like)
    if not is_employer(request.user):
        messages.error(request, "Only employers can view applicant profiles.")
        return redirect("home")

    target_user = get_object_or_404(User, username=username)
    profile = get_object_or_404(UserProfile, user=target_user)
    resume = Resume.objects.filter(user=target_user).order_by("-created_at").first() if Resume else None

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
            "resume": resume,
            "is_owner": False,
        },
    )


# ----------------------------- Own profile ------------------------------
@login_required
def user_profile_view(request):
    """
    Own profile view.
    - Produces `skills_json` for the slide-out panel:
      {"selected": [...], "suggested": [...]}
    - Supports both TextField (comma-separated) and ManyToMany for resume.skills.
    """
    # Get the user’s profile (404 if the profile truly doesn’t exist)
    profile = get_object_or_404(UserProfile, user=request.user)

    # Latest resume for this user (ok if None)
    resume = Resume.objects.filter(user=request.user).order_by("-created_at").first()

    # ---- Build selected skills ----
    selected_skills = []

    if resume:
        # Case A: ManyToMany-like (has .all attribute)
        if hasattr(resume, "skills") and hasattr(getattr(resume, "skills"), "all"):
            # Convert related objects to plain strings
            selected_skills = [str(getattr(s, "name", s)).strip()
                               for s in resume.skills.all()
                               if str(getattr(s, "name", s)).strip()]
        else:
            # Case B: TextField (comma-separated)
            raw = getattr(resume, "skills", "") or ""
            selected_skills = [s.strip() for s in raw.split(",") if s.strip()]

    # ---- Suggested skills (relatable to reentry + entry-level pathways) ----
    # Prefer centralized curated list if available; fall back to a small default
    suggested_skills = (
        RELATABLE_SKILLS or [
            "Customer Service", "Teamwork", "Communication", "Problem Solving",
            "Warehouse Operations", "Forklift Operation", "Janitorial Services",
            "Landscaping", "Food Safety", "Line Cook", "Cash Handling",
            "Microsoft Word", "Microsoft Excel", "Basic Computer Use",
        ]
    )

    # Deduplicate + don’t suggest ones already selected
    selected_set = {s.lower() for s in selected_skills}
    suggested_clean = [s for s in suggested_skills if s.lower() not in selected_set]

    # JSON the shape the front-end expects
    skills_payload = {
        "selected": selected_skills,
        "suggested": suggested_clean
    }
    # mark_safe because you render with {{ skills_json|safe }} into a <script> tag
    skills_json = mark_safe(json.dumps(skills_payload))

    context = {
        "user": request.user,
        "profile": profile,
        "resume": resume,
        "US_STATES": US_STATES,
        "ETHNICITY_CHOICES": ETHNICITY_CHOICES,
        "skills_json": skills_json,
        "is_owner": True,  # you’re in the owner view
    }
    return render(request, "profiles/user_profile.html", context)

# ----------------------------- Updates: Personal ------------------------
@require_POST
@login_required
@require_POST
@login_required
def update_personal_info(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    first = (request.POST.get("firstname") or "").strip()
    last  = (request.POST.get("lastname") or "").strip()
    phone = (request.POST.get("phone_number") or "").strip()
    email = (request.POST.get("personal_email") or "").strip()
    state = (request.POST.get("state") or "").strip()
    city  = (request.POST.get("city") or "").strip()
    street = (request.POST.get("street_address") or "").strip()
    zip_code = (request.POST.get("zip_code") or "").strip()

    errors = {}
    if not first: errors["firstname"] = "First name is required."
    if not last:  errors["lastname"]  = "Last name is required."

    if errors:
        return json_err(errors) if is_ajax(request) else redirect("my_profile")

    # Use Django User as the source of truth for names
    u = request.user
    u.first_name, u.last_name = first, last
    u.save(update_fields=["first_name", "last_name"])

    # Mirror to profile if you keep duplicates
    if hasattr(profile, "firstname"): profile.firstname = first
    if hasattr(profile, "lastname"):  profile.lastname  = last
    profile.phone_number = phone
    profile.personal_email = email
    profile.state = state
    profile.city = city
    if hasattr(profile, "street_address"):
        profile.street_address = street
    if hasattr(profile, "zip_code"):
        profile.zip_code = zip_code
    profile.save()

    updated = {
        "firstname": first,
        "lastname": last,
        "full_name": f"{first} {last}",
        "initials": (first[:1] + last[:1]).upper(),
        "phone_number": phone,
        "personal_email": email,
        "state": state,
        "city": city,
        "street_address": street,
        "zip_code": zip_code,
    }
    if is_ajax(request):
        return json_ok(updated)
    # Non-AJAX: allow caller to specify a return URL
    next_url = (request.POST.get("next") or "").strip()
    if next_url:
        return redirect(next_url)
    return redirect("my_profile")


# ----------------------------- Updates: Emergency -----------------------
@require_POST
@login_required
def update_emergency_contact(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    data = {
      "emergency_contact_firstname": (request.POST.get("emergency_contact_firstname") or "").strip(),
      "emergency_contact_lastname":  (request.POST.get("emergency_contact_lastname") or "").strip(),
      "emergency_contact_relationship": (request.POST.get("emergency_contact_relationship") or "").strip(),
      "emergency_contact_phone": (request.POST.get("emergency_contact_phone") or "").strip(),
      "emergency_contact_email": (request.POST.get("emergency_contact_email") or "").strip(),
    }

    errors = {}
    if not data["emergency_contact_firstname"]: errors["emergency_contact_firstname"] = "Required."
    if not data["emergency_contact_lastname"]:  errors["emergency_contact_lastname"]  = "Required."
    if errors:
      return json_err(errors) if is_ajax(request) else redirect("my_profile")

    for k, v in data.items():
      setattr(profile, k, v)
    profile.save()

    updated = {**data, "emergency_contact_fullname": f"{data['emergency_contact_firstname']} {data['emergency_contact_lastname']}".strip()}
    return json_ok(updated) if is_ajax(request) else redirect("my_profile")


# ----------------------------- Updates: Employment ----------------------
@require_POST
@login_required
def update_employment_info(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    # Map incoming form field names → model fields
    field_map = {
        "authorized_us": "work_in_us",
        "sponsorship_needed": "sponsorship_needed",
        "disability": "disability",
        "lgbtq": "lgbtq",
        "gender": "gender",
        "veteran_status": "veteran_status",
        "status": "status",
    }

    for post_key, model_field in field_map.items():
        if post_key in request.POST and hasattr(profile, model_field):
            setattr(profile, model_field, request.POST.get(post_key))
    profile.save()

    # Return keys the frontend expects (see profile_panels.js mapping)
    updated = {
        "work_in_us": getattr(profile, "work_in_us", ""),
        "sponsorship_needed": getattr(profile, "sponsorship_needed", ""),
        "disability": getattr(profile, "disability", ""),
        "lgbtq": getattr(profile, "lgbtq", ""),
        "gender": getattr(profile, "gender", ""),
        "veteran_status": getattr(profile, "veteran_status", ""),
        "status": getattr(profile, "status", ""),
    }
    return json_ok(updated) if is_ajax(request) else redirect("my_profile")


# ----------------------------- Updates: Demographics --------------------
@require_POST
@login_required
def update_demographics(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    payload = {
        "gender": (request.POST.get("gender") or "").strip(),
        "ethnicity": (request.POST.get("ethnicity") or "").strip(),
        "race": (request.POST.get("race") or "").strip(),
        "disability_explanation": (request.POST.get("disability_explanation") or "").strip(),
        "veteran_explanation": (request.POST.get("veteran_explanation") or "").strip(),
    }

    for k, v in payload.items():
        if hasattr(profile, k):
            setattr(profile, k, v)
    profile.save()

    updated = {
        **payload,
        "pill_text": ", ".join([x for x in [payload["gender"], payload["ethnicity"], payload["race"]] if x]),
    }
    return json_ok(updated) if is_ajax(request) else redirect("my_profile")


# ----------------------------- Updates: Bio -----------------------------
@require_POST
@login_required
def update_bio(request):
    if request.method != "POST":
        return redirect("my_profile")
    profile = get_object_or_404(UserProfile, user=request.user)
    bio = (request.POST.get("bio") or "").strip()
    profile.bio = bio
    profile.save()
    return json_ok({"bio": bio}) if is_ajax(request) else redirect("my_profile")


# ----------------------------- Updates: Skills (Resume M2M) ------------
@require_POST
@login_required
def update_skills(request):
    if not (Resume and Skill):
        return json_err({"form": "Resume/Skill models are not available."}, status=501)

    resume = Resume.objects.filter(user=request.user).order_by("-created_at").first()
    if not resume:
        # Create a lightweight resume record so skills can be managed from profile
        try:
            resume = Resume.objects.create(user=request.user)
        except Exception:
            return json_err({"form": "No resume found and could not create one."}, status=500)

    existing = {s.name.lower(): s for s in resume.skills.all()}

    def _parse_list(raw: str) -> list[str]:
        raw = (raw or "").strip()
        if not raw:
            return []
        # Hidden inputs may contain JSON (preferred) or comma-separated strings (fallback)
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except Exception:
            pass
        # Fallback: CSV
        return [s.strip() for s in raw.split(",") if s.strip()]

    to_add = _parse_list(request.POST.get("add_skills", ""))
    to_remove = _parse_list(request.POST.get("remove_skills", ""))

    # Add
    for name in to_add:
        key = name.lower()
        if key not in existing:
            obj, _ = Skill.objects.get_or_create(name=name)
            existing[key] = obj

    # Remove
    for name in to_remove:
        existing.pop(name.lower(), None)

    resume.skills.set([s.id for s in existing.values()])
    skills_sorted = sorted((s.name for s in existing.values()), key=str.lower)
    return json_ok({"skills": skills_sorted}) if is_ajax(request) else redirect("my_profile")


# ----------------------------- Profile picture -------------------------
@login_required
def update_profile_picture(request):
    """
    Handle profile picture upload.
    - Validates image header via Pillow.
    - Saves to UserProfile.profile_picture.
    - On non-AJAX, redirects back to /profile/.
    """
    if request.method == "POST" and "profile_picture" in request.FILES:
        image_file = request.FILES["profile_picture"]
        try:
            img = Image.open(image_file)
            img.verify()  # quick header check
            if img.format and img.format.lower() not in {"jpeg", "jpg", "png", "gif"}:
                messages.error(request, "Unsupported image format. Use JPEG, PNG, or GIF.")
                return redirect("my_profile")
        except UnidentifiedImageError:
            messages.error(request, "Invalid image file. Please upload a real image.")
            return redirect("my_profile")

        profile = get_object_or_404(UserProfile, user=request.user)
        profile.profile_picture = image_file
        profile.save()
        messages.success(request, "Profile picture updated successfully.")
    return redirect("my_profile")


@login_required
def remove_profile_picture(request):
    """
    Remove current user's profile picture and return to profile.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.profile_picture:
        profile.profile_picture.delete(save=False)
        profile.profile_picture = None
        profile.save(update_fields=["profile_picture"])
        messages.success(request, "Your profile picture has been removed.")
    else:
        messages.info(request, "You don't have a profile picture set.")
    return redirect("my_profile")


# ----------------------------- Background image -------------------------
@login_required
def update_profile_background(request):
    """Upload and set the user's profile hero background image."""
    if request.method == "POST" and "background_image" in request.FILES:
        image_file = request.FILES["background_image"]
        try:
            img = Image.open(image_file)
            img.verify()
            if img.format and img.format.lower() not in {"jpeg", "jpg", "png", "gif", "webp"}:
                messages.error(request, "Unsupported image format. Use JPEG, PNG, GIF, or WebP.")
                return redirect("my_profile")
        except UnidentifiedImageError:
            messages.error(request, "Invalid image file. Please upload a real image.")
            return redirect("my_profile")

        profile = get_object_or_404(UserProfile, user=request.user)
        profile.background_image = image_file
        profile.save(update_fields=["background_image"])
        messages.success(request, "Background image updated.")
    return redirect("my_profile")


@login_required
def remove_profile_background(request):
    """Remove the user's background image."""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.background_image:
        try:
            profile.background_image.delete(save=False)
        except Exception:
            pass
        profile.background_image = None
        profile.save(update_fields=["background_image"])
        messages.success(request, "Background image removed.")
    else:
        messages.info(request, "No background image to remove.")
    return redirect("my_profile")


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
    # Get or create an EmployerProfile linked to the current user so the page always has data to show/edit
    # Lazy import to avoid any circular import surprises at module load time
    from .forms import EmployerProfileForm

    employer_profile, _ = EmployerProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Bind submitted values and files (for logo uploads)
        form = EmployerProfileForm(request.POST, request.FILES, instance=employer_profile)
        if form.is_valid():
            form.save()
            # After saving, redirect back to this page (named URL: employer_profile)
            return redirect('employer_profile')
    else:
        # First page load or GET after save: show current values
        form = EmployerProfileForm(instance=employer_profile)

    # Supply current jobs and view-all link like the public page
    try:
        from reroute_business.job_list.models import Job
        jobs_qs = Job.objects.filter(is_active=True, employer=request.user).order_by('-created_at')
        total_jobs = jobs_qs.count()
        jobs = list(jobs_qs[:3])
    except Exception:
        jobs, total_jobs = [], 0

    from django.urls import reverse
    view_all_url = None
    try:
        view_all_base = reverse('opportunities')
        view_all_url = f"{view_all_base}?employer={request.user.username}"
    except Exception:
        pass

    return render(
        request,
        "profiles/employer_profile.html",
        {
            "employer_profile": employer_profile,
            "form": form,
            "jobs": jobs,
            "total_jobs": total_jobs,
            "view_all_url": view_all_url,
        },
    )


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
    return redirect("profiles:my_profile")


# ----------------------------- Subscription Settings --------------------
@login_required
def subscription_settings(request):
    """
    Show the user's subscription details.
    - Get or create Subscription row for the user.
    - If the user is not an employer, enforce 'Free' plan.
    - Provide a pricing_url that targets the correct tab (user vs employer).
    """
    sub, _ = Subscription.objects.get_or_create(user=request.user)

    employer = is_employer(request.user)

    # If not employer, force plan to Free and active True
    if not employer and sub.plan_name != Subscription.PLAN_FREE:
        sub.plan_name = Subscription.PLAN_FREE
        sub.active = True
        sub.expiry_date = None
        try:
            sub.save(update_fields=["plan_name", "active", "expiry_date"])
        except Exception:
            pass

    # Email verified? Can be disabled globally to simplify testing
    is_verified = True
    if not getattr(settings, 'DISABLE_ALLAUTH_EMAIL_VERIFICATION', True):
        if EmailAddress is not None:
            try:
                is_verified = EmailAddress.objects.filter(user=request.user, verified=True).exists()
            except Exception:
                is_verified = True

    # Compute pricing URL with tab param
    from django.urls import reverse, NoReverseMatch
    try:
        if employer:
            pricing_url = reverse('pricing') + '?tab=employer'
        else:
            pricing_url = reverse('pricing') + '?tab=user'
    except NoReverseMatch:
        pricing_url = '/'

    context = {
        "subscription": sub,
        "is_employer": employer,
        "is_verified": is_verified,
        "pricing_url": pricing_url,
    }
    return render(request, "profiles/settings_subscription.html", context)


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
