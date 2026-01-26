from __future__ import annotations

from typing import Optional

try:
    from reroute_business.core.models import OnboardingEvent
except Exception:
    OnboardingEvent = None  # type: ignore


def log_onboarding_event(user, event: str, *, once: bool = False) -> Optional[OnboardingEvent]:
    if OnboardingEvent is None:
        return None
    try:
        if once and OnboardingEvent.objects.filter(user=user, event=event).exists():
            return None
        return OnboardingEvent.objects.create(user=user if getattr(user, "is_authenticated", False) else None, event=event)
    except Exception:
        return None
