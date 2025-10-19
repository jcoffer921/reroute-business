from __future__ import annotations

from django.http import HttpRequest
from django.conf import settings
from django.shortcuts import redirect

try:
    from allauth.account.models import EmailAddress
except Exception:  # Guard if allauth import fails
    EmailAddress = None


class EnforceVerifiedEmailMiddleware:
    """
    Redirects authenticated users without a verified email to a verify notice page.
    Skips API, auth, static, admin, and the verify/resend pages themselves.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Globally disable via settings flag for testing/demo
        if getattr(settings, 'DISABLE_ALLAUTH_EMAIL_VERIFICATION', False):
            return self.get_response(request)

        # Fast-path: only care about authenticated users
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            # Allow staff/superusers to bypass to avoid lockouts
            if not (user.is_staff or user.is_superuser):
                if not self._allow_path(request.path, request):
                    if EmailAddress is not None:
                        try:
                            is_verified = EmailAddress.objects.filter(user=user, verified=True).exists()
                        except Exception:
                            is_verified = True
                    else:
                        is_verified = True

                    if not is_verified:
                        return redirect('verify_email_notice')

        return self.get_response(request)

    def _allow_path(self, path: str, request: HttpRequest) -> bool:
        # Skip for API/JSON endpoints
        accept = (request.headers.get('Accept') or '').lower()
        if path.startswith('/api/') or 'application/json' in accept:
            return True

        # Allowlist of paths that should not be intercepted
        allow_prefixes = (
            '/accounts/',          # allauth flows incl. confirm
            '/logout/',
            '/admin/',
            '/static/', '/media/',
            '/verify-email/', '/resend-verification/',
            '/privacy', '/terms',  # legal pages
        )
        return path.startswith(allow_prefixes)
