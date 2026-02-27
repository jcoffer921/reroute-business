from __future__ import annotations

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def _resolve_user_by_email(self, email: str):
        User = get_user_model()
        users_qs = User.objects.filter(email__iexact=email, is_active=True).order_by("id")
        users = list(users_qs[:10])
        if not users:
            return None
        if len(users) == 1:
            return users[0]

        # Prefer a single verified allauth email owner when duplicates exist.
        try:
            from allauth.account.models import EmailAddress

            verified_rows = (
                EmailAddress.objects
                .filter(email__iexact=email, verified=True, user__is_active=True)
                .select_related("user")
                .order_by("-primary", "user_id")
            )
            verified_users = []
            seen_user_ids = set()
            for row in verified_rows:
                if row.user_id in seen_user_ids:
                    continue
                seen_user_ids.add(row.user_id)
                verified_users.append(row.user)
            if len(verified_users) == 1:
                return verified_users[0]
            if verified_users:
                return verified_users[0]
        except Exception:
            pass

        # Deterministic fallback: oldest active account with this email.
        return users[0]

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = (sociallogin.user.email or "").strip().lower()
        if not email:
            return

        extra = sociallogin.account.extra_data or {}
        verified = extra.get("email_verified")
        if verified is None:
            verified = extra.get("verified_email")
        if verified is None:
            verified = extra.get("verified")
        if verified is False:
            return

        user = self._resolve_user_by_email(email)
        if user is None:
            return

        # If multiple legacy accounts share an email, continue with a deterministic match
        # so Google sign-in works instead of hard-failing.
        User = get_user_model()
        if User.objects.filter(email__iexact=email).count() > 1:
            messages.warning(
                request,
                "Multiple accounts share this email. We signed you into the oldest active account.",
            )

        sociallogin.connect(request, user)
