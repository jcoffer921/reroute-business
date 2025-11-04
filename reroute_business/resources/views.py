# resources/views.py
import json
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from reroute_business.blog.models import BlogPost
from .models import (
    ResourceModule,
    Lesson,
    LessonQuestion,
    LessonChoice,
    LessonAttempt,
    LessonProgress,
)


def resource_list(request):
    """
    Resources landing page with inline Learning Modules.
    - Queries all ResourceModule records ordered by most recent, passing them
      to the template so videos can render inline (no external redirects).
    """
    modules = ResourceModule.objects.all().order_by('-created_at')
    lessons = Lesson.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'resources/resource_list.html', {
        'modules': modules,
        'lessons': lessons,
    })


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
