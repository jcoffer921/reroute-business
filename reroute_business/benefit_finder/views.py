import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST


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

    return JsonResponse({"ok": True, "completed": True})
