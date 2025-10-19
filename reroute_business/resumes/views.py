# views.py
from io import BytesIO
import json
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string, get_template
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from core.utils.analytics import track_event

"""
Avoid importing heavy optional deps at module import time.
WeasyPrint requires system libraries (cairo/pango); import it lazily
inside the view that needs it to prevent 500s when opening other pages.
"""

from profiles.models import UserProfile
from core.constants import RELATABLE_SKILLS
from core.models import Skill

from .models import (
    Resume, ContactInfo, Education, Experience,
    EducationEntry, ExperienceEntry
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
def resume_welcome(request):
    return render(request, 'resumes/welcome.html')


@login_required
def create_resume(request):
    # Single entry point for builder flow
    return redirect('resumes:resume_contact_info')

# ------------------ Imported Resume Views ------------------

@login_required
def resume_import(request, resume_id):
    """
    Show imported resume details. Also allows "Save to profile" (POST).
    """
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)

    if request.method == "POST":
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
    """
    Step 1: user-provided contact info (builder).
    """
    resume = _get_or_create_resume(request.user)
    # Do NOT create ContactInfo until we have valid POSTed data.
    try:
        contact_info = resume.contact_info
    except ContactInfo.DoesNotExist:
        contact_info = None

    if request.method == 'POST':
        contact_form = ContactInfoForm(request.POST, instance=contact_info)
        if contact_form.is_valid():
            obj = contact_form.save(commit=False)
            obj.resume = resume
            obj.save()
            # Sync resume header fields for final rendering
            try:
                full_name = (contact_form.cleaned_data.get('full_name') or '').strip()
                summary_text = (request.POST.get('summary') or '').strip()
                updates = []
                if full_name and full_name != (resume.full_name or ''):
                    resume.full_name = full_name
                    updates.append('full_name')
                if summary_text and summary_text != (resume.summary or ''):
                    resume.summary = summary_text
                    updates.append('summary')
                if updates:
                    resume.save(update_fields=updates)
            except Exception:
                # Non-fatal: do not block the flow if optional fields fail
                pass
            # Analytics: resume contact info saved (builder step)
            try:
                track_event(event_type='resume_builder_contact_saved', user=request.user, metadata={'resume_id': resume.id})
            except Exception:
                pass
            return redirect('resumes:resume_education_step')
    else:
        contact_form = ContactInfoForm(instance=contact_info)

    return render(request, 'resumes/steps/contact_info_step.html', {
        'contact_form': contact_form,
        'resume_summary': getattr(resume, 'summary', ''),
    })


@login_required
def education_step(request):
    """
    Step 2: builder education entries. We replace existing builder entries
    on each POST to keep the step idempotent.
    """
    resume = _get_or_create_resume(request.user)
    formset = EducationFormSet(queryset=Education.objects.filter(resume=resume))

    if request.method == 'POST':
        formset = EducationFormSet(request.POST)
        if formset.is_valid():
            Education.objects.filter(resume=resume).delete()
            for form in formset:
                cd = getattr(form, 'cleaned_data', None) or {}
                # Skip rows marked for deletion or empty rows
                if not cd or cd.get('DELETE'):
                    continue
                instance = form.save(commit=False)
                instance.resume = resume
                instance.save()
            try:
                track_event(event_type='resume_builder_education_saved', user=request.user, metadata={'resume_id': resume.id, 'rows': len(formset.forms)})
            except Exception:
                pass
            return redirect('resumes:resume_experience_step')

    return render(request, 'resumes/steps/education_step.html', {'formset': formset})


@login_required
def experience_step(request):
    """
    Step 3: builder experience entries. Same idempotent pattern as education.
    """
    resume = _get_or_create_resume(request.user)
    formset = ExperienceFormSet(queryset=Experience.objects.filter(resume=resume))

    if request.method == 'POST':
        formset = ExperienceFormSet(request.POST)
        if formset.is_valid():
            Experience.objects.filter(resume=resume).delete()
            for form in formset:
                cd = getattr(form, 'cleaned_data', None) or {}
                if not cd or cd.get('DELETE'):
                    continue
                instance = form.save(commit=False)
                instance.resume = resume
                instance.save()
            try:
                track_event(event_type='resume_builder_experience_saved', user=request.user, metadata={'resume_id': resume.id, 'rows': len(formset.forms)})
            except Exception:
                pass
            return redirect('resumes:resume_skills_step')

    return render(request, 'resumes/steps/experience_step.html', {'formset': formset})


@login_required
def skills_step(request):
    """
    Step 4: Skills. The template expects:
      - hidden textarea 'selected_skills' (CSV)
      - context vars: 'initial_skills' (list[str]), 'suggested_skills' (list[str])
    """
    resume = _get_or_create_resume(request.user)

    if request.method == 'POST':
        # Form posts CSV of skills via the hidden <textarea name="selected_skills">
        csv = request.POST.get('selected_skills', '')
        names = [s for s in (x.strip() for x in csv.split(',')) if s]

        # Replace existing skills with normalized set
        resume.skills.clear()
        for raw in names:
            norm = _normalize_skill_name(raw)
            if not norm:
                continue
            skill, _ = Skill.objects.get_or_create(name=norm)
            resume.skills.add(skill)

        # Optional: Certifications textarea where each line is a cert name
        certs_text = (request.POST.get('certifications') or '').strip()
        try:
            if hasattr(resume, 'certifications'):
                resume.certifications = certs_text
                resume.save(update_fields=['certifications'])
        except Exception:
            pass

        # Continue to your preview/created page
        try:
            track_event(event_type='resume_builder_skills_saved', user=request.user, metadata={'resume_id': resume.id, 'skills_count': len(names)})
        except Exception:
            pass
        return redirect('resumes:created_resume_view', resume_id=resume.id)

    # For initial hydration, show what the resume already has
    initial_skills = [s.name for s in resume.skills.all()]

    # Pull 20–30 sensible suggestions (you can tune this slice)
    suggested_skills = RELATABLE_SKILLS[:30]

    return render(request, 'resumes/steps/skills_step.html', {
        'initial_skills': initial_skills,
        'suggested_skills': suggested_skills,
    })

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
    education_entries = list(resume.education.all()) or list(resume.education_entries.all())
    experience_entries = list(resume.experiences.all()) or list(resume.experience_entries.all())
    contact_info = getattr(resume, 'contact_info', None)

    # If you need profile data:
    profile = UserProfile.objects.filter(user=request.user).first()

    return render(request, 'resumes/created_resume_view.html', {
        'resume': resume,
        'profile': profile,
        'contact_info': contact_info,
        'education_entries': education_entries,
        'experience_entries': experience_entries,
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
    return redirect('dashboard')
