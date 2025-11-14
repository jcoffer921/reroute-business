# resources/views.py
import json
from datetime import datetime
from urllib.parse import quote

from django.conf import settings
from django.http import JsonResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from reroute_business.blog.models import BlogPost
from .models import (
    Module,
    ModuleQuizScore,
    Lesson,
    LessonQuestion,
    LessonChoice,
    LessonAttempt,
    LessonProgress,
)


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
    return render(request, 'resources/resource_list.html', {
        'modules': modules,
        'lessons': lessons,
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
    if yt_id:
        return f"https://i.ytimg.com/vi/{yt_id}/hqdefault.jpg"
    if module.video_url and str(module.video_url).lower().endswith('.mp4'):
        return _build_svg_poster(module.title)
    return _build_svg_poster(module.title)


@ensure_csrf_cookie
def module_detail(request, pk: int):
    module = get_object_or_404(Module, pk=pk)
    yt_id = _extract_youtube_id_simple(module.video_url or '') if module.video_url else ''
    poster_url = _module_poster_url(module, yt_id)
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
        if has_relational_questions:
            try:
                qid = int(item.get('question_id'))
                aid = int(item.get('answer_id'))
            except (TypeError, ValueError):
                continue
            if qid and aid:
                submitted[qid] = aid
        else:
            qid = str(item.get('question_id') or '').strip()
            aid = str(item.get('answer_id') or '').strip()
            if qid and aid:
                submitted[qid] = aid

    if has_relational_questions:
        questions = list(module.questions.all().order_by('order', 'id'))
        total_questions = len(questions)
    else:
        questions = _inline_quiz_questions(module)
        total_questions = len(questions)
    attempted = 0
    correct = 0

    for question in questions:
        if has_relational_questions:
            selected_id = submitted.get(question.id)
            if not selected_id:
                continue
            attempted += 1
            choice = next((choice for choice in question.answers.all() if choice.id == selected_id), None)
            if choice and choice.is_correct:
                correct += 1
        else:
            qid = str(question['id'])
            selected_id = submitted.get(qid)
            if not selected_id:
                continue
            attempted += 1
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
    related_articles = BlogPost.objects.filter(category='legal', published=True).order_by('-created_at')[:3]
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
