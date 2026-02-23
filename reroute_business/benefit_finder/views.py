import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from reroute_business.core.utils.analytics import track_event


QUESTION_IDS = {
    "age_range",
    "zip_code",
    "recently_released",
    "employment_status",
    "housing_status",
    "valid_id",
    "childcare_need",
    "transportation",
    "language_preference",
    "immediate_needs",
}

QUESTION_TYPES = {"single", "multi", "zip"}

BENEFIT_FINDER_EVENTS = {
    "bf_started",
    "bf_resumed",
    "bf_question_answered",
    "bf_step_next",
    "bf_step_back",
    "bf_validation_error",
    "bf_saved",
    "bf_low_data_toggled",
    "bf_plan_viewed",
    "bf_checklist_item_toggled",
    "bf_checklist_reset",
    "bf_category_opened",
    "bf_resources_near_me_opened",
    "bf_reentry_org_opened",
    "bf_download_print",
    "bf_completed",
}


def wizard(request):
    return render(request, 'benefit_finder/wizard.html')


@login_required
@require_POST
def mark_complete(request):
    """
    Persist Benefit Finder completion in session so dashboard can surface
    the Action Plan entry point for the current user.
    """
    payload = {}
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        payload = {}

    request.session["benefit_finder_completed"] = True
    request.session["benefit_finder_completed_at"] = timezone.now().isoformat()
    if isinstance(payload, dict) and payload.get("from_results"):
        request.session["benefit_finder_last_source"] = "results"
    request.session.modified = True

    track_event(
        event_type="benefit_finder_event",
        request=request,
        metadata={
            "feature": "benefit_finder",
            "name": "bf_completed",
            "source": "results" if isinstance(payload, dict) and payload.get("from_results") else "unknown",
        },
    )

    return JsonResponse({"ok": True, "completed": True})


def _as_int(value, minimum=None, maximum=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None
    return number


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None


@require_POST
def track_interaction(request):
    payload = {}
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        payload = {}

    if not isinstance(payload, dict):
        return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)

    event_name = payload.get("name")
    if event_name not in BENEFIT_FINDER_EVENTS:
        return JsonResponse({"ok": False, "error": "invalid_event"}, status=400)

    metadata = {
        "feature": "benefit_finder",
        "name": event_name,
    }

    question_id = payload.get("question_id")
    if question_id in QUESTION_IDS:
        metadata["question_id"] = question_id

    question_type = payload.get("question_type")
    if question_type in QUESTION_TYPES:
        metadata["question_type"] = question_type

    category_key = payload.get("category")
    if isinstance(category_key, str) and category_key:
        metadata["category"] = category_key[:64]

    source = payload.get("source")
    if isinstance(source, str) and source:
        metadata["source"] = source[:64]

    for key, bounds in {
        "step": (1, 10),
        "from_step": (1, 10),
        "to_step": (1, 10),
        "total_steps": (1, 20),
        "selected_count": (0, 50),
        "checklist_completed": (0, 25),
        "checklist_total": (0, 25),
        "categories_count": (0, 20),
    }.items():
        value = _as_int(payload.get(key), minimum=bounds[0], maximum=bounds[1])
        if value is not None:
            metadata[key] = value

    for key in {"is_valid", "low_data_mode", "has_zip", "has_language"}:
        value = _as_bool(payload.get(key))
        if value is not None:
            metadata[key] = value

    track_event(
        event_type="benefit_finder_event",
        request=request,
        metadata=metadata,
    )
    return JsonResponse({"ok": True})
