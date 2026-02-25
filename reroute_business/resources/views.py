# resources/views.py
import json
from datetime import datetime
from urllib.parse import quote, urlparse, parse_qs, urlencode, urlunparse

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.utils.translation import gettext as _
from reroute_business.blog.models import BlogPost
from reroute_business.job_list.utils.location import zip_to_point
from .templatetags.resources_extras import youtube_embed_url
from .models import (
    Feature,
    ResourceOrganization,
    Module,
    ModuleQuizScore,
    ModuleQuizOpenResponse,
    QuizQuestion,
    Lesson,
    LessonQuestion,
    LessonChoice,
    LessonAttempt,
    LessonProgress,
)

if settings.USE_GIS:
    from django.contrib.gis.db.models.functions import Distance

DIRECTORY_DISCLAIMER = (
    'ReRoute is an independent platform. Resource information is compiled from publicly available sources and may change. '
    'ReRoute does not imply partnership or endorsement unless a listing is marked with a Verified Partner badge. '
    'Verified badges will appear only for organizations that have formally partnered with ReRoute.'
)

PHILADELPHIA_ZIP_AREAS = {
    "19102": "Center City",
    "19103": "Center City West / Rittenhouse",
    "19104": "West Philly / University City",
    "19106": "Old City / Society Hill",
    "19107": "Washington Square West / Chinatown",
    "19111": "Northeast Philly",
    "19114": "Northeast Philly",
    "19115": "Somerton",
    "19116": "Northeast Philly",
    "19119": "Northwest Philly / Mt. Airy",
    "19120": "Olney / Logan",
    "19121": "North Philly",
    "19122": "North Philly / Temple Area",
    "19123": "Northern Liberties / Fishtown",
    "19124": "Frankford",
    "19125": "Fishtown / Kensington",
    "19126": "East Oak Lane",
    "19127": "Manayunk",
    "19128": "Roxborough / Manayunk",
    "19130": "Fairmount / Art Museum",
    "19131": "West Park / Wynnefield",
    "19132": "North Philly",
    "19133": "Kensington / Fairhill",
    "19134": "Port Richmond / Kensington",
    "19135": "Tacony / Holmesburg",
    "19136": "Northeast Philly",
    "19137": "Bridesburg",
    "19138": "West Oak Lane",
    "19139": "West Philly",
    "19140": "Hunting Park / Nicetown",
    "19141": "Logan / Fern Rock",
    "19142": "Southwest Philly",
    "19143": "Southwest / West Philly",
    "19144": "Germantown",
    "19145": "South Philly",
    "19146": "South Philly / Graduate Hospital",
    "19147": "South Philly / Queen Village",
    "19148": "South Philly",
    "19149": "Northeast Philly",
    "19150": "Cedarbrook",
    "19151": "West Philly",
    "19152": "Rhawnhurst / Northeast",
    "19153": "Eastwick / Southwest Philly",
}


def _phone_href(raw_phone: str, explicit_href: str) -> str:
    href = (explicit_href or "").strip()
    if href:
        return href
    digits = "".join(ch for ch in (raw_phone or "") if ch.isdigit())
    return f"+{digits}" if digits else ""


def _zip_area_label(zip_code: str) -> str:
    normalized = (zip_code or "").strip()
    if not normalized:
        return ""
    area = PHILADELPHIA_ZIP_AREAS.get(normalized)
    if area:
        return area
    return _("Philadelphia")


def _hydrate_missing_resource_geo_points():
    if not settings.USE_GIS:
        return
    missing_zip_rows = (
        ResourceOrganization.objects.filter(is_active=True, geo_point__isnull=True)
        .exclude(zip_code__exact="")
        .values_list("zip_code", flat=True)
        .distinct()
    )

    point_by_zip = {}
    for raw_zip in missing_zip_rows:
        point = zip_to_point(raw_zip)
        if point:
            normalized = (raw_zip or "").split("-")[0][:5]
            point_by_zip[normalized] = point

    if not point_by_zip:
        return

    for normalized_zip, point in point_by_zip.items():
        ResourceOrganization.objects.filter(
            is_active=True,
            geo_point__isnull=True,
            zip_code=normalized_zip,
        ).update(geo_point=point)


def _resource_to_payload(resource: ResourceOrganization) -> dict:
    category_label = resource.get_category_display() if resource.category else ""
    categories = [category_label] if category_label else []
    feature_qs = resource.features.filter(is_active=True).order_by("label")
    feature_labels = [feature.label for feature in feature_qs]
    feature_slugs = [feature.slug for feature in feature_qs]

    if not feature_labels and resource.legacy_features:
        feature_labels = [str(value).replace("_", " ").title() for value in resource.legacy_features]
        feature_slugs = [str(value) for value in resource.legacy_features]

    combined_tags = categories + feature_labels
    visible_tags = combined_tags[:5]
    hidden_tag_count = max(0, len(combined_tags) - len(visible_tags))

    languages_supported = list(resource.languages_supported or [])
    cultural_competency = list(resource.cultural_competency or [])
    what_to_bring = list(resource.what_to_bring or [])

    distance_miles = None
    distance_obj = getattr(resource, "distance", None)
    if distance_obj is not None:
        try:
            distance_miles = round(float(distance_obj.mi), 1)
        except Exception:
            distance_miles = None

    is_verified_partner = bool(getattr(resource, "is_verified", False))

    return {
        "slug": resource.slug,
        "name": resource.name,
        "categories": categories,
        "features": feature_labels,
        "feature_slugs": feature_slugs,
        "address_line": resource.address_line,
        "neighborhood": resource.neighborhood,
        "transit_line": resource.transit_line,
        "zip_code": resource.zip_code,
        "hours": resource.hours,
        "phone": resource.phone,
        "phone_href": _phone_href(resource.phone, resource.phone_href),
        "website": resource.website,
        "overview": resource.overview,
        "what_to_expect": resource.what_to_expect,
        "who_can_use_this": resource.who_can_use_this,
        "what_to_bring": what_to_bring,
        "how_to_apply": resource.how_to_apply,
        "getting_there": resource.getting_there or resource.transit_line,
        "languages_supported": languages_supported,
        "cultural_competency": cultural_competency,
        "childcare_support": resource.childcare_support,
        "card_tags": visible_tags,
        "hidden_tag_count": hidden_tag_count,
        "distance_miles": distance_miles,
        "is_verified_partner": is_verified_partner,
    }


def _inline_quiz_questions(module):
    """
    Backwards compatibility helper: normalize Module.quiz_data->questions into the
    same structure returned by relational QuizQuestion/QuizAnswer objects.
    """
    questions = []
    data = module.quiz_data or {}
    raw_questions = data.get('questions') if isinstance(data, dict) else None
    if not isinstance(raw_questions, list):
        return questions

    for idx, raw in enumerate(raw_questions, 1):
        if not isinstance(raw, dict):
            continue
        prompt = (raw.get('prompt') or '').strip()
        if not prompt:
            continue
        raw_choices = raw.get('choices')
        if not isinstance(raw_choices, list):
            continue

        norm_choices = []
        for c_idx, choice in enumerate(raw_choices, 1):
            if not isinstance(choice, dict):
                continue
            text = (choice.get('text') or '').strip()
            if not text:
                continue
            choice_id = choice.get('id')
            if choice_id in (None, ''):
                choice_id = f"{idx}_{c_idx}"
            norm_choices.append({
                'id': str(choice_id),
                'text': text,
                'is_correct': bool(choice.get('is_correct') or choice.get('correct')),
            })
        if not norm_choices:
            continue

        q_id = raw.get('id')
        if q_id in (None, ''):
            q_id = str(idx)
        questions.append({
            'id': str(q_id),
            'prompt': prompt,
            'order': raw.get('order') or idx,
            'qtype': QuizQuestion.QTYPE_MULTIPLE_CHOICE,
            'choices': norm_choices,
        })
    return questions


def resource_list(request):
    """
    Resources landing page with inline Learning Modules.
    - Queries all Module records ordered by most recent, passing them
      to the template so videos can render inline (no external redirects).
    """
    modules = Module.objects.all().order_by('-created_at')
    lessons = Lesson.objects.filter(is_active=True).order_by('-created_at')
    featured_resource_obj = (
        ResourceOrganization.objects
        .filter(is_active=True, is_verified=True)
        .order_by("name")
        .first()
    )
    featured_resource = _resource_to_payload(featured_resource_obj) if featured_resource_obj else None
    return render(request, 'resources/resource_list.html', {
        'modules': modules,
        'lessons': lessons,
        'featured_resource': featured_resource,
    })


@require_GET
def resources_directory(request):
    zip_code = (request.GET.get('zip') or '').strip()
    if not zip_code.isdigit() or len(zip_code) != 5:
        zip_code = ''

    selected_features = [slug for slug in request.GET.getlist("features") if slug]

    if zip_code:
        _hydrate_missing_resource_geo_points()

    queryset = ResourceOrganization.objects.filter(is_active=True)
    if selected_features:
        queryset = queryset.filter(features__slug__in=selected_features).distinct()

    user_point = zip_to_point(zip_code) if (settings.USE_GIS and zip_code) else None
    if settings.USE_GIS and user_point:
        queryset = queryset.annotate(distance=Distance("geo_point", user_point)).order_by(
            F("is_verified").desc(),
            F("distance").asc(nulls_last=True),
            "name",
        )
    else:
        queryset = queryset.order_by("-is_verified", "name")

    prepared_resources = [_resource_to_payload(resource) for resource in queryset]

    paginator = Paginator(prepared_resources, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    page_params = request.GET.copy()
    page_params.pop('page', None)
    pagination_query = page_params.urlencode()

    filter_features = list(Feature.objects.filter(is_active=True).order_by("label"))
    filter_categories = [label for _, label in ResourceOrganization.CATEGORY_CHOICES]

    return render(request, 'resources/directory/directory_list.html', {
        'resources': page_obj.object_list,
        'page_obj': page_obj,
        'filter_categories': filter_categories,
        'filter_features': filter_features,
        'selected_features': selected_features,
        'selected_zip': zip_code,
        'selected_zip_area': _zip_area_label(zip_code) if zip_code else "",
        'pagination_query': pagination_query,
        'directory_disclaimer': DIRECTORY_DISCLAIMER,
    })


@require_GET
def resource_directory_detail(request, slug):
    resource_obj = get_object_or_404(ResourceOrganization, slug=slug, is_active=True)
    resource = _resource_to_payload(resource_obj)

    return render(request, 'resources/directory/directory_detail.html', {
        'resource': resource,
        'directory_disclaimer': DIRECTORY_DISCLAIMER,
    })


# ------------------ Module Detail (video + quiz) ------------------

def _extract_youtube_id_simple(url: str) -> str:
    try:
        from urllib.parse import urlparse, parse_qs
        u = urlparse(url or '')
        host = (u.netloc or '').lower()
        path = u.path or ''
        if 'youtube.com/embed/' in url or 'youtube-nocookie.com/embed/' in url:
            return path.rstrip('/').split('/')[-1]
        if host.endswith('youtu.be'):
            return path.lstrip('/').split('/')[0]
        if 'watch' in path:
            q = parse_qs(u.query or '')
            return (q.get('v') or [''])[0]
        if '/shorts/' in path:
            parts = [p for p in path.split('/') if p]
            try:
                i = parts.index('shorts')
                return parts[i+1]
            except Exception:
                return ''
    except Exception:
        return ''
    return ''


def _build_svg_poster(text: str) -> str:
    title = (text or 'Learning Module').strip()[:48] or 'Learning Module'
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 675'>"
        "<defs>"
        "<linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0%' stop-color='%23f5f7fb'/>"
        "<stop offset='100%' stop-color='%23dbeafe'/>"
        "</linearGradient>"
        "</defs>"
        "<rect width='1200' height='675' fill='url(%23g)'/>"
        "<text x='50%' y='50%' font-family='Helvetica,Arial,sans-serif' font-size='56' "
        "fill='%234a6cff' text-anchor='middle' dominant-baseline='middle'>"
        f"{title}"
        "</text>"
        "</svg>"
    )
    return "data:image/svg+xml;utf8," + quote(svg)


def _module_poster_url(module, yt_id: str) -> str:
    if module.poster_image:
        try:
            return module.poster_image.url
        except Exception:
            pass
    if yt_id:
        return f"https://i.ytimg.com/vi/{yt_id}/hqdefault.jpg"
    if module.video_url and str(module.video_url).lower().endswith('.mp4'):
        return _build_svg_poster(module.title)
    return _build_svg_poster(module.title)


def _is_mp4_source(url: str) -> bool:
    try:
        parsed = urlparse(str(url or "").strip())
        return (parsed.path or "").lower().endswith(".mp4")
    except Exception:
        return False


def _append_query_defaults(url: str, defaults: dict) -> str:
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query or "")
        for key, value in defaults.items():
            if key not in query:
                query[key] = [str(value)]
        flat_query = urlencode({k: v[-1] if isinstance(v, list) else v for k, v in query.items()})
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, flat_query, parsed.fragment))
    except Exception:
        return url


def _module_embed_url(raw_video_url: str) -> str:
    normalized = youtube_embed_url(raw_video_url or "").strip()
    if not normalized:
        return ""
    if "youtube.com/embed/" not in normalized and "youtube-nocookie.com/embed/" not in normalized:
        return ""
    return _append_query_defaults(normalized, {
        "rel": 0,
        "modestbranding": 1,
        "playsinline": 1,
    })


@ensure_csrf_cookie
def module_detail(request, pk: int):
    module = get_object_or_404(Module, pk=pk)
    module_embed_url = _module_embed_url(module.video_url or '')
    yt_id = _extract_youtube_id_simple(module_embed_url or module.video_url or '') if module.video_url else ''
    poster_url = _module_poster_url(module, yt_id)
    module_is_mp4 = _is_mp4_source(module.video_url)
    duration_label = getattr(module, 'duration_label', None) or 'Self-paced video'
    user_score = None
    if request.user.is_authenticated:
        user_score = ModuleQuizScore.objects.filter(module=module, user=request.user).first()
    question_count = module.questions.count()
    if not question_count:
        question_count = len(_inline_quiz_questions(module))
    estimated_minutes = max(3, int(question_count or 3))
    progress_percent = 0
    if user_score and user_score.total_questions:
        try:
            ratio = user_score.score / max(user_score.total_questions, 1)
            progress_percent = max(0, min(100, round(ratio * 100)))
        except Exception:
            progress_percent = 0
    return render(request, 'resources/modules/module_detail.html', {
        'module': module,
        'yt_id': yt_id,
        'module_embed_url': module_embed_url,
        'module_is_mp4': module_is_mp4,
        'video_poster': poster_url,
        'video_duration_label': duration_label,
        'estimated_minutes': estimated_minutes,
        'user_score': user_score,
        'can_submit_quiz': request.user.is_authenticated,
        'question_count': question_count,
        'progress_percent': progress_percent,
    })


@require_GET
def module_quiz_schema(request, pk: int):
    module = get_object_or_404(Module.objects.prefetch_related('questions__answers'), pk=pk)

    qs = list(module.questions.all().order_by('order', 'id'))
    if qs:
        questions_payload = []
        for question in qs:
            choices = []
            for choice in question.answers.all().order_by('id'):
                choices.append({
                    'id': str(choice.id),
                    'text': choice.text,
                    'is_correct': choice.is_correct,
                })
            questions_payload.append({
                'id': str(question.id),
                'prompt': question.prompt,
                'order': question.order,
                'qtype': question.qtype,
                'choices': choices,
            })
    else:
        questions_payload = _inline_quiz_questions(module)

    payload = {
        'module_id': module.id,
        'title': module.title,
        'questions': questions_payload,
    }

    if request.user.is_authenticated:
        existing = ModuleQuizScore.objects.filter(module=module, user=request.user).first()
        if existing:
            payload['user_score'] = {
                'score': existing.score,
                'total_questions': existing.total_questions,
                'updated_at': existing.updated_at.isoformat(),
            }

    return JsonResponse(payload)


@require_POST
@csrf_protect
def module_quiz_submit(request, pk: int):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=403)
    module = get_object_or_404(Module.objects.prefetch_related('questions__answers'), pk=pk)
    has_relational_questions = module.questions.exists()
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    answers = data.get('answers') or []
    if not isinstance(answers, list):
        return JsonResponse({'error': 'Answers must be a list.'}, status=400)

    # Build lookup of submitted answers keyed by question id
    submitted = {}
    for item in answers:
        raw_qid = item.get('question_id')
        if raw_qid in (None, ''):
            continue
        if has_relational_questions:
            try:
                key = int(raw_qid)
            except (TypeError, ValueError):
                continue
        else:
            key = str(raw_qid)
        record = submitted.setdefault(key, {})
        answer_id = item.get('answer_id')
        if answer_id not in (None, ''):
            if has_relational_questions:
                try:
                    record['answer_id'] = int(answer_id)
                except (TypeError, ValueError):
                    pass
            else:
                record['answer_id'] = str(answer_id)
        if 'text_answer' in item:
            record['text_answer'] = item.get('text_answer')

    if has_relational_questions:
        questions = list(module.questions.all().order_by('order', 'id'))
        graded_questions = [q for q in questions if q.qtype != QuizQuestion.QTYPE_OPEN]
        total_questions = len(graded_questions)
    else:
        questions = _inline_quiz_questions(module)
        total_questions = len(questions)
    attempted = 0
    correct = 0

    for question in questions:
        if has_relational_questions:
            key = question.id
            qtype = question.qtype
        else:
            key = str(question['id'])
            qtype = QuizQuestion.QTYPE_MULTIPLE_CHOICE

        record = submitted.get(key) or {}

        if qtype == QuizQuestion.QTYPE_OPEN:
            text_answer = (record.get('text_answer') or '').strip()
            if text_answer:
                ModuleQuizOpenResponse.objects.update_or_create(
                    module=module,
                    question=question,
                    user=request.user,
                    defaults={'response_text': text_answer},
                )
            else:
                ModuleQuizOpenResponse.objects.filter(
                    module=module,
                    question=question,
                    user=request.user,
                ).delete()
            continue

        selected_id = record.get('answer_id')
        if not selected_id:
            continue
        attempted += 1
        if has_relational_questions:
            choice = next((choice for choice in question.answers.all() if choice.id == selected_id), None)
            if choice and choice.is_correct:
                correct += 1
        else:
            choices = question.get('choices') or []
            match = next((choice for choice in choices if str(choice.get('id')) == selected_id), None)
            if match and match.get('is_correct'):
                correct += 1

    score_obj, _ = ModuleQuizScore.objects.update_or_create(
        module=module,
        user=request.user,
        defaults={'score': correct, 'total_questions': total_questions},
    )

    payload = {
        'message': 'Score saved.',
        'score': correct,
        'total_questions': total_questions,
        'attempted': attempted,
        'percent': round((correct / total_questions) * 100, 2) if total_questions else 0.0,
        'updated_at': score_obj.updated_at.isoformat(),
    }
    return JsonResponse(payload)


def interview_prep(request):
    return render(request, 'resources/job_tools/interview_prep.html')

def email_guidance(request):
    return render(request, 'resources/job_tools/email_guidance.html')

def legal_aid(request):
    related_articles = BlogPost.objects.filter(visibility=BlogPost.VISIBILITY_PUBLIC, published=True).filter(Q(category=BlogPost.CATEGORY_REENTRY) | Q(category='legal')).order_by('-created_at')[:3]
    return render(request, 'resources/reentry_help/legal_aid.html', {
        'related_articles': related_articles
    })

def housing(request):
    return render(request, 'resources/reentry_help/housing.html')

def counseling(request):
    return render(request, 'resources/reentry_help/counseling.html')

def tech_courses(request):
    return render(request, 'resources/job_tools/tech_courses.html')

def job_tools_index(request):
    return render(request, 'resources/job_tools/index.html')

def reentry_help_index(request):
    return render(request, 'resources/reentry_help/index.html')

def resources_verification(request):
    return render(request, 'resources/verification.html')


# ------------------ Interactive Lessons ------------------

def _ensure_session(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


@ensure_csrf_cookie
def lesson_detail(request, slug):
    lesson = get_object_or_404(Lesson, slug=slug, is_active=True)
    # Use a generic template for any lesson; front-end JS loads schema via API
    return render(request, 'resources/lessons/lesson_detail.html', {
        'lesson': lesson,
    })


@require_GET
def lesson_schema(request, slug):
    lesson = get_object_or_404(Lesson, slug=slug, is_active=True)
    # Build schema without revealing which choice is correct
    questions = []
    for q in lesson.questions.filter(active=True).order_by('order'):
        item = {
            'id': q.id,
            'order': q.order,
            'timestamp_seconds': q.timestamp_seconds,
            'prompt': q.prompt,
            'qtype': q.qtype,
            'is_required': q.is_required,
            'is_scored': q.is_scored,
            'choices': [],
        }
        if q.qtype == LessonQuestion.TYPE_MULTIPLE_CHOICE:
            for c in q.choices.all().order_by('position'):
                item['choices'].append({
                    'id': c.id,
                    'label': c.label,
                    'text': c.text,
                })
        questions.append(item)

    # Load any prior progress
    session_key = _ensure_session(request)
    prog = None
    if request.user.is_authenticated:
        prog = LessonProgress.objects.filter(lesson=lesson, user=request.user).order_by('-updated_at').first()
    if not prog:
        prog = LessonProgress.objects.filter(lesson=lesson, session_key=session_key).order_by('-updated_at').first()

    progress = None
    if prog:
        progress = {
            'correct_count': prog.correct_count,
            'scored_count': prog.scored_count,
            'accuracy_percent': prog.accuracy_percent,
            'last_video_time': prog.last_video_time,
            'last_answered_question_order': prog.last_answered_question_order,
            'completed_at': prog.completed_at.isoformat() if prog.completed_at else None,
        }

    payload = {
        'lesson': {
            'id': lesson.id,
            'title': lesson.title,
            'slug': lesson.slug,
            'description': lesson.description,
            'video_url': lesson.video_static_path,
            'youtube_video_id': getattr(lesson, 'youtube_video_id', None),
            'duration_seconds': lesson.duration_seconds,
        },
        'questions': questions,
        'progress': progress,
    }
    return JsonResponse(payload)


@require_POST
@csrf_protect
def lesson_attempt(request, slug):
    lesson = get_object_or_404(Lesson, slug=slug, is_active=True)
    session_key = _ensure_session(request)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    qid = data.get('question_id')
    choice_id = data.get('selected_choice_id')
    open_text = (data.get('open_text') or '').strip()
    current_time = float(data.get('current_time') or 0)

    question = get_object_or_404(LessonQuestion, id=qid, lesson=lesson)

    # Count attempts to compute the next attempt number for this user/session
    base_qs = LessonAttempt.objects.filter(question=question)
    if request.user.is_authenticated:
        base_qs = base_qs.filter(user=request.user)
    else:
        base_qs = base_qs.filter(session_key=session_key)
    attempt_number = base_qs.count() + 1

    is_correct = False
    selected_choice = None
    if question.qtype == LessonQuestion.TYPE_MULTIPLE_CHOICE:
        if not choice_id:
            return JsonResponse({'error': 'selected_choice_id required'}, status=400)
        selected_choice = get_object_or_404(LessonChoice, id=choice_id, question=question)
        is_correct = bool(selected_choice.is_correct)
    else:
        # Open-ended is considered complete when submitted, not scored
        is_correct = False

    attempt = LessonAttempt.objects.create(
        question=question,
        user=request.user if request.user.is_authenticated else None,
        session_key=session_key,
        selected_choice=selected_choice,
        open_text=open_text,
        is_correct=is_correct,
        attempt_number=attempt_number,
        video_time=current_time,
    )

    # Update progress
    prog_qs = LessonProgress.objects.filter(lesson=lesson)
    if request.user.is_authenticated:
        prog_qs = prog_qs.filter(user=request.user)
    else:
        prog_qs = prog_qs.filter(session_key=session_key)
    prog = prog_qs.first()
    if not prog:
        prog = LessonProgress.objects.create(
            lesson=lesson,
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key,
            scored_count=lesson.questions.filter(is_scored=True, active=True).count(),
        )

    # Recompute correct_count from attempts for scored questions
    scored_qs = lesson.questions.filter(is_scored=True, active=True)
    correct_count = 0
    for sq in scored_qs:
        # last correct attempt exists?
        sq_attempts = LessonAttempt.objects.filter(question=sq)
        if request.user.is_authenticated:
            sq_attempts = sq_attempts.filter(user=request.user)
        else:
            sq_attempts = sq_attempts.filter(session_key=session_key)
        if sq_attempts.filter(is_correct=True).exists():
            correct_count += 1

    accuracy = round((correct_count / max(prog.scored_count, 1)) * 100) if prog.scored_count else 0
    prog.correct_count = correct_count
    prog.accuracy_percent = accuracy
    # last_video_time may update via progress endpoint separately
    prog.save(update_fields=[
        'correct_count', 'accuracy_percent', 'updated_at'
    ])

    return JsonResponse({
        'attempt_id': attempt.id,
        'is_correct': is_correct,
        'correct_count': correct_count,
        'scored_count': prog.scored_count,
        'accuracy_percent': accuracy,
    })


@require_POST
@csrf_protect
def lesson_progress(request, slug):
    lesson = get_object_or_404(Lesson, slug=slug, is_active=True)
    session_key = _ensure_session(request)
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    last_video_time = float(data.get('last_video_time') or 0)
    last_answered_order = int(data.get('last_answered_question_order') or 0)
    completed = bool(data.get('completed') or False)
    raw_state = data.get('raw_state')

    prog_qs = LessonProgress.objects.filter(lesson=lesson)
    if request.user.is_authenticated:
        prog_qs = prog_qs.filter(user=request.user)
    else:
        prog_qs = prog_qs.filter(session_key=session_key)
    prog = prog_qs.first()
    if not prog:
        prog = LessonProgress.objects.create(
            lesson=lesson,
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key,
            scored_count=lesson.questions.filter(is_scored=True, active=True).count(),
        )

    prog.last_video_time = last_video_time
    prog.last_answered_question_order = max(prog.last_answered_question_order, last_answered_order)
    if raw_state is not None:
        prog.raw_state = raw_state
    if completed and not prog.completed_at:
        prog.completed_at = datetime.utcnow()
    prog.save()

    return JsonResponse({
        'ok': True,
        'completed_at': prog.completed_at.isoformat() if prog.completed_at else None,
        'last_video_time': prog.last_video_time,
        'last_answered_question_order': prog.last_answered_question_order,
    })
