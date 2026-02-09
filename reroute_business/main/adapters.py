from __future__ import annotations

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
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

        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        sociallogin.connect(request, user)
