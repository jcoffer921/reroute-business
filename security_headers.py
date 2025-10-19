# security_headers.py  (put in your project and add to MIDDLEWARE after SecurityMiddleware)
from django.utils.deprecation import MiddlewareMixin

class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # --- Content Security Policy ---
        # Start with a conservative baseline. Switch 'report-only' to 'Content-Security-Policy'
        # after you verify in the browser console that nothing breaks.
        # Allow iframing only for the resume style preview route (same-origin)
        frame_ancestors = "'self'" if request.path.startswith('/resumes/preview-style/') else "'none'"
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' https:; "
            # Allow embedding third-party iframes such as Google reCAPTCHA
            "frame-src 'self' https:; "
            f"frame-ancestors {frame_ancestors}; "
            "upgrade-insecure-requests"
        )
        response.headers.setdefault("Content-Security-Policy", csp)

        # --- Permissions-Policy: lock down browser features ---
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

        return response
