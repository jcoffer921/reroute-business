# security_headers.py  (put in your project and add to MIDDLEWARE after SecurityMiddleware)
from django.utils.deprecation import MiddlewareMixin

class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # --- Content Security Policy ---
        # Start with a conservative baseline. Switch 'report-only' to 'Content-Security-Policy'
        # after you verify in the browser console that nothing breaks.
        # Allow iframing only for the resume style preview route (same-origin)
        frame_ancestors = "'self'" if request.path.startswith('/resumes/preview-style/') else "'none'"
        # Allow-list common third-party providers used in the app explicitly to
        # avoid overly-broad https: while staying CSP-compliant.
        script_src = " ".join([
            "'self'",
            "'unsafe-inline'",  # consider migrating to nonces/hashes later
            # App integrations
            "https://www.youtube.com",
            "https://www.gstatic.com",
            # Google reCAPTCHA
            "https://www.google.com",
            "https://www.gstatic.com/recaptcha",
        ])

        frame_src = " ".join([
            "'self'",
            # YouTube embeds
            "https://www.youtube.com",
            # Google reCAPTCHA challenge frame
            "https://www.google.com",
        ])

        connect_src = " ".join([
            "'self'",
            # If any XHRs/WebSockets are made to third-parties, add here.
            "https://www.google.com",
        ])

        csp = (
            "default-src 'self'; "
            f"script-src {script_src}; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data: https:; "
            f"connect-src {connect_src}; "
            f"frame-src {frame_src}; "
            f"frame-ancestors {frame_ancestors}; "
            "upgrade-insecure-requests"
        )
        response.headers.setdefault("Content-Security-Policy", csp)

        # --- Permissions-Policy: lock down browser features ---
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

        return response
