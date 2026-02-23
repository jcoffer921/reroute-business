# views.py
from io import BytesIO
import json
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.template.loader import render_to_string, get_template
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from reroute_business.core.utils.analytics import track_event

"""
Avoid importing heavy optional deps at module import time.
WeasyPrint requires system libraries (cairo/pango); import it lazily
inside the view that needs it to prevent 500s when opening other pages.
"""

from reroute_business.profiles.models import UserProfile
from reroute_business.core.utils.onboarding import log_onboarding_event
from reroute_business.core.constants import RELATABLE_SKILLS
from reroute_business.core.models import Skill

from .models import (
    Resume, ContactInfo, Education, Experience,
    EducationEntry, ExperienceEntry, EducationType, ResumeSkill
)
from .forms import (
    ContactInfoForm, EducationForm, EducationFormSet,
    ExperienceForm, ExperienceFormSet
)
from .utils.resume_parser import (
    read_upload_file, extract_resume_information, validate_file_extension,
    validate_file_size
)
from .utils.summaries import random_generic_summary

# Lightweight employer check to avoid importing view helpers across apps
def _is_employer_user(user) -> bool:
    try:
        if not getattr(user, 'is_authenticated', False):
            return False
        # Prefer group check; mirror logic used elsewhere (Employer/Employers)
        return user.groups.filter(name__in=["Employer", "Employers"]).exists()
    except Exception:
        return False

# ------------------ Helpers ------------------

def _normalize_skill_name(name: str) -> str:
    # Lowercase + collapse whitespace so “Forklift ” == “forklift”
    return " ".join((name or "").strip().split()).lower()


def _get_or_create_resume(user):
    """
    Get the most recent resume for a user, or create an empty one.
    """
    resume = Resume.objects.filter(user=user).order_by('-created_at').first()
    if not resume:
        resume = Resume.objects.create(user=user)
    return resume


RESUME_STEP_ORDER = ["basics", "experience", "skills", "education", "review"]
RESUME_SECTION_DEFAULT = ["basics", "experience", "skills", "education"]


def _normalize_phone(raw: str) -> str:
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def _ensure_section_order(resume: Resume) -> None:
    if not resume.section_order:
        resume.section_order = RESUME_SECTION_DEFAULT[:]
        resume.save(update_fields=["section_order"])


def _get_or_create_created_resume(user):
    resume = Resume.objects.filter(user=user, is_imported=False).order_by("-created_at").first()
    if not resume:
        resume = Resume.objects.create(user=user, is_imported=False, section_order=RESUME_SECTION_DEFAULT[:])
    else:
        _ensure_section_order(resume)
    return resume


def _next_incomplete_step(resume: Resume) -> str:
    if not resume.step_basics_complete:
        return "basics"
    if not resume.step_experience_complete:
        return "experience"
    if not resume.step_skills_complete:
        return "skills"
    if not resume.step_education_complete:
        return "education"
    return "review"


def _build_step_context(resume: Resume, active_step: str) -> dict:
    return {
        "steps": [
            {"key": "basics", "label": "Basics", "number": 1, "complete": resume.step_basics_complete},
            {"key": "experience", "label": "Experience", "number": 2, "complete": resume.step_experience_complete},
            {"key": "skills", "label": "Skills", "number": 3, "complete": resume.step_skills_complete},
            {"key": "education", "label": "Education", "number": 4, "complete": resume.step_education_complete},
            {"key": "review", "label": "Review", "number": 5, "complete": resume.step_review_complete},
        ],
        "active_step": active_step,
    }


def _get_skill_categories():
    """
    Provide consistent buckets for the skills step (front-end uses this).
    """
    return {
        "Trade / Hands-On": RELATABLE_SKILLS[:13],
        "Soft Skills": RELATABLE_SKILLS[13:24],
        "Job Readiness": RELATABLE_SKILLS[24:38],
        "Entrepreneurial": RELATABLE_SKILLS[38:]
    }

# ------------------ Entry / Welcome ------------------

@login_required
def resume_landing(request):
    try:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if profile.onboarding_step in {"start", "profile_started", "profile_completed"}:
            profile.onboarding_step = "resume_started"
            profile.save(update_fields=["onboarding_step"])
    except Exception:
        pass

    try:
        log_onboarding_event(request.user, "resume_started", once=True)
    except Exception:
        pass

    return render(request, "resumes/landing.html")


@login_required
def resume_welcome(request):
    return resume_landing(request)


@login_required
def resume_start(request):
    created_resume = Resume.objects.filter(user=request.user, is_imported=False).order_by("-created_at").first()
    imported_exists = Resume.objects.filter(user=request.user, is_imported=True).exists()
    has_in_progress = bool(created_resume and not created_resume.is_complete)
    next_step = _next_incomplete_step(created_resume) if created_resume else "basics"

    continue_url = reverse(f"resumes:resume_{next_step}_step")
    return render(request, "resumes/start.html", {
        "imported_exists": imported_exists,
        "created_resume": created_resume,
        "has_in_progress": has_in_progress,
        "continue_url": continue_url,
    })


@login_required
def create_resume(request):
    # Single entry point for builder flow
    resume = _get_or_create_created_resume(request.user)
    _ensure_section_order(resume)
    step = _next_incomplete_step(resume)
    return redirect(f"resumes:resume_{step}_step")

# ------------------ Imported Resume Views ------------------

@login_required
def resume_import(request, resume_id):
    """
    Show imported resume details. Also allows "Save to profile" (POST).
    """
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)

    if request.method == "POST":
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.onboarding_step = "resume_completed"
            profile.update_onboarding_flags(resume=resume)
            profile.save(update_fields=["onboarding_step", "onboarding_completed", "early_access_priority"])
        except Exception:
            pass
        try:
            log_onboarding_event(request.user, "resume_completed", once=True)
        except Exception:
            pass
        messages.success(request, "✅ Resume saved to your profile successfully!")
        # Send users back to the dashboard's user view
        return redirect("dashboard:user")

    # Prepare developer-friendly extracted JSON (ai_summary currently stores JSON)
    extracted = {}
    try:
        if resume.ai_summary:
            extracted = json.loads(resume.ai_summary)
    except Exception:
        extracted = {}

    # Build a personalized, professional 2–3 sentence summary
    def build_summary_snippet() -> str:
        sentences: list[str] = []

        # Name and location
        try:
            ci = getattr(resume, 'contact_info', None)
        except Exception:
            ci = None
        name = (getattr(ci, 'full_name', '') or resume.full_name or '').strip()
        city = (getattr(ci, 'city', '') or '').strip()
        state = (getattr(ci, 'state', '') or '').strip()
        loc = f" in {city}, {state}" if city and state else (f" in {city}" if city else "")

        # Experience highlights
        exp = list(resume.experience_entries.all()[:3])
        role = (exp[0].job_title if exp and getattr(exp[0], 'job_title', '') else '').strip()
        companies = [e.company.strip() for e in exp if getattr(e, 'company', '')]
        companies = [c for c in companies if c]
        companies = list(dict.fromkeys(companies))  # dedupe, preserve order

        subject = name or "This candidate"
        if role and companies:
            sentences.append(f"{subject}{loc} is a {role.lower()} with hands-on experience at {', '.join(companies[:2])}.")
        elif role:
            sentences.append(f"{subject}{loc} is a {role.lower()} with a track record of delivering results.")
        elif companies:
            sentences.append(f"{subject}{loc} brings experience from {', '.join(companies[:2])}.")
        else:
            sentences.append(f"{subject}{loc} is an experienced professional with a solid work history.")

        # Skills highlights (top 4)
        try:
            skill_names = [s.name for s in resume.skills.all()[:10]]
        except Exception:
            skill_names = []
        if skill_names:
            top = [s.title() for s in skill_names[:4]]
            sentences.append(f"Strengths include {', '.join(top)}.")

        # Education and certifications
        edu = list(resume.education_entries.all()[:1])
        cert_line = (resume.certifications or '').strip()
        cert_one = ''
        if cert_line:
            # Take the first non-empty certification line
            for ln in cert_line.splitlines():
                ln = (ln or '').strip()
                if ln:
                    cert_one = ln
                    break
        if edu:
            deg = (edu[0].degree or '').strip()
            school = (edu[0].school_name or '').strip()
            year = (edu[0].graduation_year or '').strip()
            edu_phrase = ""
            if deg and school:
                edu_phrase = f"{deg} from {school}{f' ({year})' if year else ''}"
            elif school:
                edu_phrase = f"education from {school}{f' ({year})' if year else ''}"
            if edu_phrase and cert_one:
                sentences.append(f"Education includes {edu_phrase}, and certifications such as {cert_one}.")
            elif edu_phrase:
                sentences.append(f"Education includes {edu_phrase}.")
            elif cert_one:
                sentences.append(f"Holds certifications such as {cert_one}.")
        elif cert_one:
            sentences.append(f"Holds certifications such as {cert_one}.")

        # Limit to 3 sentences
        return " ".join(sentences[:3])

    ai_summary_snippet = build_summary_snippet()

    return render(request, "resumes/imported_resume_view.html", {
        "resume": resume,
        "extracted_json_pretty": json.dumps(extracted, indent=2, ensure_ascii=False),
        "ai_summary_snippet": ai_summary_snippet,
    })


@login_required
def resume_upload_page(request):
    try:
        log_onboarding_event(request.user, "resume_started", once=True)
    except Exception:
        pass
    return render(request, 'resumes/import_resume.html')


@login_required
def parse_resume_upload(request):
    """
    Parse an uploaded resume, AI-extract structured fields, and persist them.
    This is wrapped in a DB transaction so partial saves do not leave
    orphaned data if parsing fails.
    """
    if request.method != "POST" or not request.FILES.get("file"):
        return JsonResponse({"error": "No file uploaded"}, status=400)

    file = request.FILES["file"]

    try:
        # --- Validate and read ---
        ext = validate_file_extension(file)
        validate_file_size(file)
        content = read_upload_file(file, ext)

        # --- Extract structured fields using the robust helper ---
        extracted = extract_resume_information(content)

        # --- Create the Resume first (so we always keep the file/raw_text) ---
        with transaction.atomic():
            resume = Resume.objects.create(
                user=request.user,
                file=file,
                raw_text=content,
                ai_summary=json.dumps(extracted),
                is_imported=True,
                summary=random_generic_summary(),  # seed with a professional generic summary
            )

            # --- Contact Info ---
            contact_data = extracted.get("contact_info") or {}
            if any(contact_data.values()):
                ContactInfo.objects.update_or_create(
                    resume=resume,
                    defaults={
                        "full_name": contact_data.get("full_name", "")[:255],
                        "email": contact_data.get("email", "")[:254],
                        "phone": contact_data.get("phone", "")[:20],
                        "city": contact_data.get("city", "")[:100],
                        "state": (contact_data.get("state") or "")[:2].upper(),
                    }
                )

            # --- Skills (normalized) ---
            for raw_name in extracted.get("skills", []):
                norm = _normalize_skill_name(raw_name)
                if not norm:
                    continue
                skill, _ = Skill.objects.get_or_create(name=norm)
                resume.skills.add(skill)

            # --- Experience Entries (imported) ---
            for item in extracted.get("experience", []):
                ExperienceEntry.objects.create(
                    resume=resume,
                    job_title=(item.get("job_title") or "")[:255],
                    company=(item.get("company") or "")[:255],
                    dates=item.get("dates", "")[:100],
                )

            # --- Education Entries (imported) ---
            for edu in extracted.get("education", []):
                EducationEntry.objects.create(
                    resume=resume,
                    school_name=(edu.get("school_name") or "")[:255],
                    degree=(edu.get("degree") or "")[:255],
                    graduation_year=(edu.get("graduation_year") or "")[:4],
                )

        # Analytics: resume imported
        try:
            track_event(event_type='resume_imported', user=request.user, metadata={'resume_id': resume.id, 'ext': ext})
        except Exception:
            pass
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.onboarding_step = "resume_completed"
            profile.update_onboarding_flags(resume=resume)
            profile.save(update_fields=["onboarding_step", "onboarding_completed", "early_access_priority"])
        except Exception:
            pass
        try:
            log_onboarding_event(request.user, "resume_completed", once=True)
        except Exception:
            pass

        # Provide a redirect URL so the front-end doesn't hardcode paths
        from django.urls import reverse
        redirect_url = reverse('resumes:imported_resume', args=[resume.id])
        return JsonResponse({
            "resume_id": resume.id,
            "message": "Parsed successfully",
            "redirect_url": redirect_url,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def upload_resume_only(request):
    """
    Store the uploaded resume file without parsing. Accepts PDF/DOCX/DOC.
    Returns JSON with a redirect URL (dashboard) on success.
    """
    if request.method != "POST" or not request.FILES.get("file"):
        return JsonResponse({"error": "No file uploaded"}, status=400)

    file = request.FILES["file"]

    # Allow a broader set for file-only uploads
    allowed = {".pdf", ".docx", ".doc"}
    ext = os.path.splitext(file.name or "")[1].lower()
    if ext not in allowed:
        return JsonResponse({"error": "Unsupported file type. Upload a PDF, DOCX, or DOC."}, status=400)

    try:
        validate_file_size(file)
        resume = Resume.objects.create(
            user=request.user,
            file=file,
            is_imported=True,
            summary=random_generic_summary(),
        )
        # Analytics: resume uploaded (file-only)
        try:
            track_event(event_type='resume_uploaded', user=request.user, metadata={'resume_id': resume.id, 'ext': ext})
        except Exception:
            pass
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.onboarding_step = "resume_completed"
            profile.update_onboarding_flags(resume=resume)
            profile.save(update_fields=["onboarding_step", "onboarding_completed", "early_access_priority"])
        except Exception:
            pass
        try:
            log_onboarding_event(request.user, "resume_completed", once=True)
        except Exception:
            pass
        # Send user to the dashboard router (chooses user/employer/admin)
        from django.urls import reverse
        redirect_url = reverse('dashboard:my_dashboard')
        return JsonResponse({
            "resume_id": resume.id,
            "message": "Uploaded successfully",
            "redirect_url": redirect_url,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def update_imported_resume(request, resume_id: int):
    """Accept JSON payload from the imported resume editor to update draft fields."""
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)

    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Update summary
    summary = (payload.get('summary') or '').strip()
    if hasattr(resume, 'summary'):
        resume.summary = summary
        resume.save(update_fields=['summary'])

    # Update experiences (backward compat: 'experiences' or new 'experiences_updates')
    for item in (payload.get('experiences_updates') or payload.get('experiences') or []) or []:
        try:
            exp = ExperienceEntry.objects.get(id=int(item.get('id') or 0), resume=resume)
            exp.job_title = (item.get('job_title') or '')[:255]
            exp.company = (item.get('company') or '')[:255]
            exp.dates = (item.get('dates') or '')[:100]
            exp.save(update_fields=['job_title', 'company', 'dates'])
        except (ExperienceEntry.DoesNotExist, ValueError):
            continue

    # Create new experiences
    for item in payload.get('experiences_creates', []) or []:
        jt = (item.get('job_title') or '').strip()[:255]
        co = (item.get('company') or '').strip()[:255]
        if not jt or not co:
            continue
        ExperienceEntry.objects.create(resume=resume, job_title=jt, company=co, dates=(item.get('dates') or '')[:100])

    # Delete experiences
    for rid in payload.get('experience_deletes', []) or []:
        try:
            ExperienceEntry.objects.filter(id=int(rid), resume=resume).delete()
        except Exception:
            continue

    # Update education
    for ed in (payload.get('education_updates') or payload.get('education') or []) or []:
        try:
            obj = EducationEntry.objects.get(id=int(ed.get('id') or 0), resume=resume)
            obj.degree = (ed.get('degree') or '')[:255]
            obj.school_name = (ed.get('school_name') or '')[:255]
            obj.graduation_year = (ed.get('graduation_year') or '')[:4]
            obj.save(update_fields=['degree', 'school_name', 'graduation_year'])
        except (EducationEntry.DoesNotExist, ValueError):
            continue

    # Create new education entries (require school_name)
    for ed in payload.get('education_creates', []) or []:
        school = (ed.get('school_name') or '').strip()[:255]
        if not school:
            continue
        EducationEntry.objects.create(
            resume=resume,
            school_name=school,
            degree=(ed.get('degree') or '')[:255],
            graduation_year=(ed.get('graduation_year') or '')[:4]
        )

    # Delete education entries
    for rid in payload.get('education_deletes', []) or []:
        try:
            EducationEntry.objects.filter(id=int(rid), resume=resume).delete()
        except Exception:
            continue

    # Update skills: if a pill text changed, re-associate to a matching skill
    for s in (payload.get('skills_updates') or payload.get('skills') or []) or []:
        try:
            sid = int(s.get('id') or 0)
            if not sid:
                continue
            old = Skill.objects.get(id=sid)
            new_name = (s.get('name') or '').strip().lower()
            if not new_name or new_name == (old.name or ''):
                continue
            new_skill, _ = Skill.objects.get_or_create(name=new_name[:255])
            resume.skills.remove(old)
            resume.skills.add(new_skill)
        except Exception:
            continue

    # Create skills: get_or_create and attach
    for s in payload.get('skills_creates', []) or []:
        name = (s.get('name') or '').strip().lower()
        if not name:
            continue
        skill, _ = Skill.objects.get_or_create(name=name[:255])
        resume.skills.add(skill)

    # Delete skills: detach association
    for rid in payload.get('skill_deletes', []) or []:
        try:
            resume.skills.remove(int(rid))
        except Exception:
            continue

    # Section order: optionally persist into ai_summary JSON so it can be reused
    try:
        ai = json.loads(resume.ai_summary) if resume.ai_summary else {}
        ai['section_order'] = payload.get('section_order') or []
        if payload.get('experience_order'):
            ai['experience_order'] = payload.get('experience_order')
        if payload.get('education_order'):
            ai['education_order'] = payload.get('education_order')
        resume.ai_summary = json.dumps(ai)
        resume.save(update_fields=['ai_summary'])
    except Exception:
        pass

    return JsonResponse({"status": "ok"})


@login_required
def discard_imported_resume(request, resume_id: int):
    """Delete the imported resume draft and return a redirect URL for the client."""
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    try:
        # Delete file if present
        if getattr(resume, 'file', None):
            try:
                resume.file.delete(save=False)
            except Exception:
                pass
        resume.delete()
        # Go back to dashboard router
        from django.urls import reverse
        return JsonResponse({"redirect_url": reverse('dashboard:my_dashboard')})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

# ------------------ Builder Steps ------------------

@login_required
def contact_info_step(request):
    return basics_step(request)


@login_required
def basics_step(request):
    """
    Step 1: Basics (contact details + headline).
    """
    resume = _get_or_create_created_resume(request.user)
    _ensure_section_order(resume)
    _ensure_section_order(resume)

    try:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if profile.onboarding_step in {"start", "profile_started", "profile_completed"}:
            profile.onboarding_step = "resume_started"
            profile.save(update_fields=["onboarding_step"])
        log_onboarding_event(request.user, "resume_started", once=True)
    except Exception:
        profile = None

    try:
        contact_info = resume.contact_info
    except ContactInfo.DoesNotExist:
        contact_info = None

    initial = {}
    if not contact_info:
        full_name = request.user.get_full_name().strip() or ""
        if profile:
            full_name = full_name or f"{profile.firstname} {profile.lastname}".strip()
        initial = {
            "full_name": full_name or request.user.username,
            "email": request.user.email or (getattr(profile, "personal_email", "") if profile else ""),
            "phone": getattr(profile, "phone_number", ""),
            "city": getattr(profile, "city", ""),
            "state": getattr(profile, "state", "")[:2].upper() if getattr(profile, "state", "") else "",
        }

    if request.method == "POST":
        contact_form = ContactInfoForm(request.POST, instance=contact_info, initial=initial)
        if contact_form.is_valid():
            obj = contact_form.save(commit=False)
            obj.resume = resume
            obj.phone = _normalize_phone(obj.phone)
            obj.save()

            resume.full_name = obj.full_name
            resume.headline = (request.POST.get("headline") or "").strip()
            resume.step_basics_complete = True
            resume.last_step = "experience"
            resume.save(update_fields=["full_name", "headline", "step_basics_complete", "last_step"])

            try:
                track_event(event_type="resume_builder_contact_saved", user=request.user, metadata={"resume_id": resume.id})
            except Exception:
                pass
            return redirect("resumes:resume_experience_step")
    else:
        contact_form = ContactInfoForm(instance=contact_info, initial=initial)

    if not resume.step_basics_complete and resume.last_step != "basics":
        resume.last_step = "basics"
        resume.save(update_fields=["last_step"])

    return render(request, "resumes/steps/basics_step.html", {
        "contact_form": contact_form,
        "resume": resume,
        "headline": resume.headline or "",
        **_build_step_context(resume, "basics"),
    })


@login_required
def education_step(request):
    """
    Step 4: Education & Training (optional).
    """
    resume = _get_or_create_created_resume(request.user)
    _ensure_section_order(resume)
    formset = EducationFormSet(queryset=Education.objects.filter(resume=resume).order_by("order", "id"))

    if request.method == "POST":
        if request.POST.get("skip") == "1":
            resume.step_education_complete = True
            resume.last_step = "review"
            resume.save(update_fields=["step_education_complete", "last_step"])
            return redirect("resumes:resume_review_step")

        formset = EducationFormSet(request.POST, queryset=Education.objects.filter(resume=resume))
        if formset.is_valid():
            saved_ids = []
            for index, form in enumerate(formset.forms):
                cd = getattr(form, "cleaned_data", None) or {}
                if not cd or cd.get("DELETE"):
                    if form.instance and form.instance.pk:
                        form.instance.delete()
                    continue
                instance = form.save(commit=False)
                instance.resume = resume
                instance.order = index
                instance.save()
                saved_ids.append(instance.id)

            resume.step_education_complete = True
            resume.last_step = "review"
            resume.save(update_fields=["step_education_complete", "last_step"])

            try:
                track_event(event_type="resume_builder_education_saved", user=request.user, metadata={"resume_id": resume.id, "rows": len(saved_ids)})
            except Exception:
                pass
            return redirect("resumes:resume_review_step")

    if not resume.step_education_complete and resume.last_step != "education":
        resume.last_step = "education"
        resume.save(update_fields=["last_step"])

    return render(request, "resumes/steps/education_step.html", {
        "formset": formset,
        "resume": resume,
        "education_types": EducationType.objects.all(),
        **_build_step_context(resume, "education"),
    })


@login_required
def experience_step(request):
    """
    Step 2: Experience entries.
    """
    resume = _get_or_create_created_resume(request.user)
    formset = ExperienceFormSet(queryset=Experience.objects.filter(resume=resume).order_by("order", "id"))

    if request.method == "POST":
        formset = ExperienceFormSet(request.POST, queryset=Experience.objects.filter(resume=resume))
        if formset.is_valid():
            saved_ids = []
            for index, form in enumerate(formset.forms):
                cd = getattr(form, "cleaned_data", None) or {}
                if not cd or cd.get("DELETE"):
                    if form.instance and form.instance.pk:
                        form.instance.delete()
                    continue
                instance = form.save(commit=False)
                instance.resume = resume
                instance.order = index
                lines = [ln.strip().lstrip("•").strip() for ln in (instance.responsibilities or "").splitlines() if ln.strip()]
                instance.responsibilities = "\n".join(lines)
                if instance.currently_work_here:
                    instance.end_year = ""
                instance.save()
                saved_ids.append(instance.id)

            resume.step_experience_complete = bool(saved_ids)
            resume.last_step = "skills"
            resume.save(update_fields=["step_experience_complete", "last_step"])

            try:
                track_event(event_type="resume_builder_experience_saved", user=request.user, metadata={"resume_id": resume.id, "rows": len(saved_ids)})
            except Exception:
                pass
            return redirect("resumes:resume_skills_step")

    if not resume.step_experience_complete and resume.last_step != "experience":
        resume.last_step = "experience"
        resume.save(update_fields=["last_step"])

    return render(request, "resumes/steps/experience_step.html", {
        "formset": formset,
        "resume": resume,
        **_build_step_context(resume, "experience"),
    })


@login_required
def skills_step(request):
    """
    Step 3: Skills & Strengths.
    """
    resume = _get_or_create_created_resume(request.user)

    if request.method == "POST":
        try:
            technical = json.loads(request.POST.get("technical_skills", "[]"))
            soft = json.loads(request.POST.get("soft_skills", "[]"))
        except Exception:
            technical = []
            soft = []

        resume.skills.clear()
        ResumeSkill.objects.filter(resume=resume).delete()

        added_ids = set()

        def _save_skills(items, category):
            for idx, raw in enumerate(items):
                norm = _normalize_skill_name(raw)
                if not norm:
                    continue
                skill, _ = Skill.objects.get_or_create(name=norm)
                if skill.id in added_ids:
                    continue
                resume.skills.add(skill)
                ResumeSkill.objects.create(resume=resume, skill=skill, category=category, order=idx)
                added_ids.add(skill.id)

        _save_skills(technical, "technical")
        _save_skills(soft, "soft")

        resume.step_skills_complete = bool(technical or soft)
        resume.last_step = "education"
        resume.save(update_fields=["step_skills_complete", "last_step"])

        try:
            track_event(event_type="resume_builder_skills_saved", user=request.user, metadata={"resume_id": resume.id, "skills_count": len(technical) + len(soft)})
        except Exception:
            pass
        return redirect("resumes:resume_education_step")

    technical_skills = list(ResumeSkill.objects.filter(resume=resume, category="technical").order_by("order").values_list("skill__name", flat=True))
    soft_skills = list(ResumeSkill.objects.filter(resume=resume, category="soft").order_by("order").values_list("skill__name", flat=True))
    if not technical_skills and not soft_skills:
        technical_skills = list(resume.skills.all().values_list("name", flat=True))

    suggested = _get_skill_categories()
    return render(request, "resumes/steps/skills_step.html", {
        "resume": resume,
        "technical_skills": technical_skills,
        "soft_skills": soft_skills,
        "suggested_technical": suggested.get("Trade / Hands-On", []) + suggested.get("Job Readiness", []),
        "suggested_soft": suggested.get("Soft Skills", []) + suggested.get("Entrepreneurial", []),
        **_build_step_context(resume, "skills"),
    })


@login_required
def basics_autosave(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    resume = _get_or_create_created_resume(request.user)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}

    try:
        contact_info = resume.contact_info
    except ContactInfo.DoesNotExist:
        contact_info = None

    updates = {}
    for key in ["full_name", "email", "phone", "city", "state"]:
        if key in data:
            updates[key] = (data.get(key) or "").strip()

    if "phone" in updates:
        updates["phone"] = _normalize_phone(updates["phone"])
    if "state" in updates:
        updates["state"] = updates["state"][:2].upper()

    if contact_info:
        for key, value in updates.items():
            setattr(contact_info, key, value or getattr(contact_info, key))
        contact_info.save()
    elif updates:
        fallback_name = request.user.get_full_name().strip() or request.user.username
        fallback_email = request.user.email or ""
        contact_info = ContactInfo.objects.create(
            resume=resume,
            full_name=updates.get("full_name") or fallback_name,
            email=updates.get("email") or fallback_email,
            phone=updates.get("phone", ""),
            city=updates.get("city", ""),
            state=updates.get("state", ""),
        )

    headline = (data.get("headline") or "").strip()
    if headline != (resume.headline or ""):
        resume.headline = headline

    resume.last_step = "basics"
    resume.step_basics_complete = bool(
        contact_info and contact_info.full_name and contact_info.email and contact_info.phone
    )
    resume.full_name = contact_info.full_name if contact_info else resume.full_name
    resume.save(update_fields=["headline", "last_step", "step_basics_complete", "full_name"])

    return JsonResponse({"status": "ok", "complete": resume.step_basics_complete})


@login_required
def experience_autosave(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    resume = _get_or_create_created_resume(request.user)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}

    roles = data.get("roles") or []
    saved_ids = []

    for index, item in enumerate(roles):
        if item.get("delete"):
            try:
                Experience.objects.filter(id=int(item.get("id") or 0), resume=resume).delete()
            except Exception:
                pass
            continue

        job_title = (item.get("job_title") or "").strip()
        company = (item.get("company") or "").strip()
        responsibilities = (item.get("responsibilities") or "").strip()
        if not job_title and not company and not responsibilities:
            continue

        instance = None
        if item.get("id"):
            try:
                instance = Experience.objects.get(id=int(item["id"]), resume=resume)
            except Exception:
                instance = None

        if not instance:
            instance = Experience(resume=resume)

        instance.role_type = (item.get("role_type") or "job")
        instance.job_title = job_title
        instance.company = company
        instance.start_year = (item.get("start_year") or "").strip()
        instance.end_year = (item.get("end_year") or "").strip()
        instance.currently_work_here = bool(item.get("currently_work_here"))
        instance.tools = (item.get("tools") or "").strip()
        lines = [ln.strip().lstrip("•").strip() for ln in responsibilities.splitlines() if ln.strip()]
        instance.responsibilities = "\n".join(lines)
        if instance.currently_work_here:
            instance.end_year = ""
        instance.order = index
        instance.save()
        saved_ids.append(instance.id)

    resume.step_experience_complete = bool(saved_ids)
    resume.last_step = "experience"
    resume.save(update_fields=["step_experience_complete", "last_step"])

    return JsonResponse({"status": "ok", "complete": resume.step_experience_complete})


@login_required
def skills_autosave(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    resume = _get_or_create_created_resume(request.user)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}

    technical = data.get("technical") or []
    soft = data.get("soft") or []

    resume.skills.clear()
    ResumeSkill.objects.filter(resume=resume).delete()

    added_ids = set()

    def _save(items, category):
        for idx, raw in enumerate(items):
            norm = _normalize_skill_name(raw)
            if not norm:
                continue
            skill, _ = Skill.objects.get_or_create(name=norm)
            if skill.id in added_ids:
                continue
            resume.skills.add(skill)
            ResumeSkill.objects.create(resume=resume, skill=skill, category=category, order=idx)
            added_ids.add(skill.id)

    _save(technical, "technical")
    _save(soft, "soft")

    resume.step_skills_complete = bool(technical or soft)
    resume.last_step = "skills"
    resume.save(update_fields=["step_skills_complete", "last_step"])

    return JsonResponse({"status": "ok", "complete": resume.step_skills_complete})


@login_required
def education_autosave(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    resume = _get_or_create_created_resume(request.user)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}

    entries = data.get("education") or []
    saved_ids = []

    for index, item in enumerate(entries):
        if item.get("delete"):
            try:
                Education.objects.filter(id=int(item.get("id") or 0), resume=resume).delete()
            except Exception:
                pass
            continue

        school = (item.get("school") or "").strip()
        edu_type_id = item.get("education_type")
        if not school and not edu_type_id and not (item.get("field_of_study") or "").strip():
            continue

        instance = None
        if item.get("id"):
            try:
                instance = Education.objects.get(id=int(item["id"]), resume=resume)
            except Exception:
                instance = None

        if not instance:
            instance = Education(resume=resume)

        if edu_type_id:
            instance.education_type_id = int(edu_type_id)
        instance.school = school
        instance.field_of_study = (item.get("field_of_study") or "").strip()
        instance.year = (item.get("year") or "").strip()
        instance.details = (item.get("details") or "").strip()
        instance.order = index
        instance.save()
        saved_ids.append(instance.id)

    resume.step_education_complete = bool(saved_ids) or bool(data.get("skipped"))
    resume.last_step = "education"
    resume.save(update_fields=["step_education_complete", "last_step"])

    return JsonResponse({"status": "ok", "complete": resume.step_education_complete})


@login_required
def review_step(request):
    resume = _get_or_create_created_resume(request.user)
    _ensure_section_order(resume)

    if request.method == "POST" and request.POST.get("action") == "save":
        resume.step_review_complete = True
        resume.is_complete = True
        resume.last_step = "review"
        resume.save(update_fields=["step_review_complete", "is_complete", "last_step"])
        return redirect("resumes:created_resume_view", resume_id=resume.id)

    contact_info = getattr(resume, "contact_info", None)
    experiences = list(Experience.objects.filter(resume=resume).order_by("order", "id"))
    educations = list(Education.objects.filter(resume=resume).order_by("order", "id"))
    technical_skills = list(ResumeSkill.objects.filter(resume=resume, category="technical").order_by("order"))
    soft_skills = list(ResumeSkill.objects.filter(resume=resume, category="soft").order_by("order"))

    if not resume.step_review_complete and resume.last_step != "review":
        resume.last_step = "review"
        resume.save(update_fields=["last_step"])

    return render(request, "resumes/steps/review_step.html", {
        "resume": resume,
        "contact_info": contact_info,
        "experiences": experiences,
        "educations": educations,
        "technical_skills": technical_skills,
        "soft_skills": soft_skills,
        "section_order": resume.section_order or RESUME_SECTION_DEFAULT,
        **_build_step_context(resume, "review"),
    })


@login_required
def review_reorder(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    resume = _get_or_create_created_resume(request.user)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}

    section_order = data.get("section_order") or []
    if section_order:
        filtered = [s for s in section_order if s in RESUME_SECTION_DEFAULT]
        for missing in RESUME_SECTION_DEFAULT:
            if missing not in filtered:
                filtered.append(missing)
        resume.section_order = filtered
        resume.save(update_fields=["section_order"])

    exp_order = data.get("experience_order") or []
    for idx, rid in enumerate(exp_order):
        try:
            Experience.objects.filter(id=int(rid), resume=resume).update(order=idx)
        except Exception:
            pass

    edu_order = data.get("education_order") or []
    for idx, rid in enumerate(edu_order):
        try:
            Education.objects.filter(id=int(rid), resume=resume).update(order=idx)
        except Exception:
            pass

    return JsonResponse({"status": "ok"})

# ------------------ Views (Preview, Created, Download) ------------------

@login_required
def created_resume_view(request, resume_id):
    """
    Final read of a created resume (builder flow), with prefetch to avoid N+1.
    Falls back to imported entries if builder sets are empty (rare).
    """
    resume = get_object_or_404(
        Resume.objects.select_related('user').prefetch_related(
            'skills', 'education', 'experiences', 'education_entries', 'experience_entries'
        ),
        id=resume_id, user=request.user
    )

    # Prefer builder data; fall back to imported entries if builder is empty.
    education_entries = list(resume.education.all().order_by("order", "id")) or list(resume.education_entries.all())
    experience_entries = list(resume.experiences.all().order_by("order", "id")) or list(resume.experience_entries.all())
    contact_info = getattr(resume, 'contact_info', None)

    # If you need profile data:
    profile = UserProfile.objects.filter(user=request.user).first()

    try:
        if profile:
            profile.onboarding_step = "resume_completed"
            profile.update_onboarding_flags(resume=resume)
            profile.save(update_fields=["onboarding_step", "onboarding_completed", "early_access_priority"])
    except Exception:
        pass
    try:
        log_onboarding_event(request.user, "resume_completed", once=True)
    except Exception:
        pass

    return render(request, 'resumes/created_resume_view.html', {
        'resume': resume,
        'profile': profile,
        'contact_info': contact_info,
        'education_entries': education_entries,
        'experience_entries': experience_entries,
        "early_access_message": (
            "ReRoute is in early access. Employers and reentry organizations are onboarding now. "
            "Completed profiles get priority access when jobs launch."
        ),
    })


@login_required
def resume_preview(request, resume_id=None):
    """
    Unified preview used by builder 'Preview' and by the standalone preview route.
    Reads *either* builder sets or imported sets transparently.
    Also accepts POST (JSON) to update basic fields quickly.
    """
    # If no ID, preview most recent; else use given
    if resume_id:
        resume = get_object_or_404(
            Resume.objects.prefetch_related('skills', 'education', 'experiences', 'education_entries', 'experience_entries'),
            id=resume_id, user=request.user
        )
    else:
        resume = Resume.objects.filter(user=request.user).order_by('-created_at').first() or Resume.objects.create(user=request.user)

    if request.method == 'POST':
        try:
            data = json.loads(request.body or "{}")
            # Optional quick updates (name, skills)
            if 'full_name' in data:
                resume.full_name = (data.get('full_name') or '')[:100]

            if 'skills' in data and isinstance(data['skills'], list):
                resume.skills.clear()
                for raw in data['skills']:
                    norm = _normalize_skill_name(str(raw))
                    if norm:
                        skill, _ = Skill.objects.get_or_create(name=norm)
                        resume.skills.add(skill)

            resume.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    # Contact info fallback
    contact_info = getattr(resume, 'contact_info', None) or {
        'email': request.user.email or "you@example.com",
        'phone': "(000) 000-0000",
        'location': "City, State",
    }

    # Prefer builder sets; fallback to imported
    education_entries = list(resume.education.all()) or list(resume.education_entries.all())
    experience_entries = list(resume.experiences.all()) or list(resume.experience_entries.all())
    skills = resume.skills.all()

    # Optional: naive skill guessing if empty and raw_text exists
    if not skills and resume.raw_text:
        lines = resume.raw_text.lower().split('\n')
        guessed = [line.strip() for line in lines if 'skill' in line or ',' in line]
        for guess in guessed[:5]:
            norm = _normalize_skill_name(guess)
            if norm:
                skill, _ = Skill.objects.get_or_create(name=norm)
                resume.skills.add(skill)
        skills = resume.skills.all()

    return render(request, 'resumes/resume_preview.html', {
        'resume': resume,
        'contact_info': contact_info,
        'raw_text': resume.raw_text,
        'education_entries': education_entries,
        'experience_entries': experience_entries,
        'skills': skills,
    })


@login_required
@csrf_exempt  # If you add proper CSRF in your JS, you can remove this.
def save_created_resume(request, resume_id):
    """
    Marks a resume as 'created' (not imported). Kept simple.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "invalid"}, status=405)

    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    try:
        resume.is_imported = False
        resume.save(update_fields=['is_imported'])
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=400)


@login_required
def download_resume(request, resume_id):
    """
    Render current resume to PDF using WeasyPrint.
    """
    # Lazy import to avoid module import errors if system libs are missing
    try:
        from weasyprint import HTML  # type: ignore
    except Exception as e:
        return HttpResponse(
            "PDF generation is not available on this server.", status=501
        )

    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    # Pick a template, falling back to simple.html if the requested template doesn't exist
    template_name = (
        f"resumes/{resume.template}.html"
        if resume.template in ['simple', 'professional', 'modern', 'reroute']
        else "resumes/simple.html"
    )
    try:
        template = get_template(template_name)
    except Exception:
        template = get_template("resumes/simple.html")
    html_string = template.render({'resume': resume})

    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(target=pdf_file)
    pdf_file.seek(0)

    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{resume.user.username}_resume.pdf"'
    return response


# ------------------ Employer Read-only Resume Access ------------------
@login_required
def employer_preview_resume(request, username: str):
    """
    Allow verified employers to preview a candidate's latest resume by username.
    Renders the selected resume style as a standalone page (read-only).
    """
    if not _is_employer_user(request.user):
        messages.error(request, "Only employers can view candidate resumes.")
        return redirect('dashboard:my_dashboard')

    target_user = get_object_or_404(User, username=username)
    resume = Resume.objects.filter(user=target_user).order_by('-created_at').first()
    if not resume:
        messages.info(request, "This candidate has not uploaded a resume yet.")
        return redirect('profiles:public_profile', username=target_user.username) if 'profiles' in request.resolver_match.namespaces else redirect('public_profile', username=target_user.username)

    # Pick a style template and render read-only
    style = resume.template if resume.template in ['simple', 'professional', 'modern', 'reroute'] else 'simple'
    template_name = f"resumes/{style}.html"
    try:
        template = get_template(template_name)
    except Exception:
        template = get_template("resumes/simple.html")
    html = template.render({'resume': resume})
    return HttpResponse(html)


@login_required
def employer_download_resume(request, username: str):
    """
    Allow employers to download a candidate's resume as PDF.
    Uses the candidate's selected style and does not allow edits.
    """
    if not _is_employer_user(request.user):
        messages.error(request, "Only employers can download candidate resumes.")
        return redirect('dashboard:my_dashboard')

    # Lazy import; server may not have PDF libs in all environments
    try:
        from weasyprint import HTML  # type: ignore
    except Exception:
        return HttpResponse("PDF generation is not available on this server.", status=501)

    target_user = get_object_or_404(User, username=username)
    resume = Resume.objects.filter(user=target_user).order_by('-created_at').first()
    if not resume:
        messages.info(request, "This candidate has not uploaded a resume yet.")
        return redirect('profiles:public_profile', username=target_user.username) if 'profiles' in request.resolver_match.namespaces else redirect('public_profile', username=target_user.username)

    style = resume.template if resume.template in ['simple', 'professional', 'modern', 'reroute'] else 'simple'
    template_name = f"resumes/{style}.html"
    try:
        template = get_template(template_name)
    except Exception:
        template = get_template("resumes/simple.html")
    html_string = template.render({'resume': resume})

    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(target=pdf_file)
    pdf_file.seek(0)

    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{username}_resume.pdf"'
    return response


@login_required
def set_resume_template(request, resume_id):
    """Update the selected template for a resume and return to the created view."""
    if request.method != 'POST':
        return redirect('resumes:created_resume_view', resume_id=resume_id)

    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    choice = (request.POST.get('template') or '').strip()
    allowed = {key for key, _ in Resume.TEMPLATE_CHOICES}
    if choice in allowed:
        resume.template = choice
        # Persist without triggering other updates
        resume.save(update_fields=['template'])
        messages.success(request, f"Resume style set to {choice.title()}.")
    else:
        messages.error(request, "Invalid template choice.")
    return redirect('resumes:created_resume_view', resume_id=resume_id)


@login_required
@xframe_options_sameorigin
def preview_style(request, resume_id):
    """Render a standalone HTML preview for a chosen resume style (for iframe)."""
    resume = get_object_or_404(
        Resume.objects.select_related('user').prefetch_related('skills', 'education', 'experiences', 'education_entries', 'experience_entries'),
        id=resume_id, user=request.user
    )
    choice = (request.GET.get('template') or resume.template or 'reroute').strip()
    allowed = {'reroute', 'professional', 'modern', 'simple'}
    if choice not in allowed:
        choice = 'reroute'

    template_name = f"resumes/{choice}.html"
    try:
        template = get_template(template_name)
    except Exception:
        template = get_template("resumes/simple.html")

    html = template.render({'resume': resume})
    resp = HttpResponse(html)
    # Ensure CSP allows this route to be embedded (middleware uses setdefault)
    resp['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
        "style-src 'self' 'unsafe-inline' https:; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'self'; "
        "upgrade-insecure-requests"
    )
    return resp


@login_required
def upload_profile_picture(request):
    """
    Store a user profile picture. Uses UserProfile instead of request.user.profile
    to avoid AttributeError if a OneToOne proxy isn't configured.
    """
    if request.method == 'POST':
        image_file = request.FILES.get('cropped_image')
        if image_file:
            profile = get_object_or_404(UserProfile, user=request.user)
            # NOTE: adjust field name if your model uses something other than 'profile_picture'
            profile.profile_picture.save(image_file.name, image_file)
            profile.save()
    return redirect('dashboard:my_dashboard')
