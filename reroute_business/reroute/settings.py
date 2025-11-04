# settings.py
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-dev-secret")

# ---------- DATABASES ----------
# Use Postgres when DATABASE_URL is present (Render/production).
# Original behavior: no SQLite fallback here.
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Project pointers
ROOT_URLCONF = 'reroute_business.reroute.urls'
WSGI_APPLICATION = 'reroute_business.reroute.wsgi.application'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'main' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Project context
                'reroute_business.main.context_processors.role_flags',
                'reroute_business.main.context_processors.unread_notifications',
            ],
        },
    },
]

# Company metadata (for templates)
COMPANY_LEGAL_NAME = os.getenv('COMPANY_LEGAL_NAME', 'ReRoute Jobs, LLC')

# ---------- DEBUG / LOGGING ----------
DEBUG = os.getenv("DEBUG", "False").lower() == "true"  # was hardcoded True
#DEBUG = False
RENDER = os.getenv("RENDER", "") != ""                 # Render sets RENDER="true" in env

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django": {"handlers": ["console"], "level": "INFO"},
    },
}


# ---------- HOSTS / CSRF ----------
# Helpers to parse comma-separated env vars safely
def _csv_env(name, default):
    raw = os.getenv(name, default)
    return [h.strip() for h in raw.split(",") if h.strip()]

ALLOWED_HOSTS = _csv_env(
    "ALLOWED_HOSTS",
    "reroute-backend.onrender.com,reroute-business.onrender.com,reroutejobs.com,www.reroutejobs.com,localhost,127.0.0.1",
)

CSRF_TRUSTED_ORIGINS = _csv_env(
    "CSRF_TRUSTED_ORIGINS",
    "https://reroute-backend.onrender.com,https://reroute-business.onrender.com,https://reroutejobs.com,https://www.reroutejobs.com,http://localhost,http://127.0.0.1",
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True


# ---------- APPS ----------
INSTALLED_APPS = [
    # local apps
    'reroute_business.main',
    'reroute_business.resumes',
    'reroute_business.dashboard',
    'reroute_business.blog',
    'reroute_business.core',
    'reroute_business.profiles',
    'reroute_business.job_list',
    'reroute_business.resources',
    'reroute_business.reentry_org',

    # default Django apps
    'django.contrib.admin',
    'django.contrib.sites',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third-party apps
    'widget_tweaks',
    'crispy_forms',
    'crispy_bootstrap4',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
]



# ---------- MIDDLEWARE ----------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # ✅ must be right after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'reroute_business.main.middleware.EnforceVerifiedEmailMiddleware',
    'reroute_business.reroute.security_headers.SecurityHeadersMiddleware',
    'reroute_business.core.middleware.pageviews.PageViewMiddleware',
]



# ---------- STATIC / MEDIA ----------
STATIC_URL = '/static/'

# Ensure Django can find the project's static assets reliably in production.
# BASE_DIR points at the repo root, while our app static lives under
# 'reroute_business/main/static'. Use the correct absolute path here.
STATICFILES_DIRS = [BASE_DIR / 'reroute_business' / 'main' / 'static']

# Where collected static files are written during build/deploy
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Use WhiteNoise compressed storage (non-manifest) to avoid manifest lookups
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# Avoid 500s if a template references a static path
# missing from the manifest (serve un-hashed file instead).
WHITENOISE_MANIFEST_STRICT = False

# Keep original, un-hashed files in STATIC_ROOT so that
# fallback lookups won't 500 if a manifest entry is missing.
WHITENOISE_KEEP_ONLY_HASHED_FILES = False

# In case collected files are missing at runtime, allow WhiteNoise
# to serve directly from finders (app/static + STATICFILES_DIRS).
# This is safe for our scale and removes 404s if collectstatic fails.
WHITENOISE_USE_FINDERS = True


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}


# ---------- EMAIL ----------
EMAIL_BACKEND = (
    'django.core.mail.backends.console.EmailBackend'
    if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = 'support@reroutejobs.com'
EMAIL_HOST_PASSWORD = 'rfwkrwlvqomsmcry'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
CONTACT_RECEIVER_EMAIL = 'support@reroutejobs.com'


# ---------- SECURITY ----------
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = not DEBUG
SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")

if not DEBUG:
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True


# ---------- i18n ----------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ---------- reCAPTCHA ----------
if DEBUG:
    RECAPTCHA_SITE_KEY = '6LchCXsrAAAAAJUK4ipb6_vBjR84Yn_1HfbUeXZQ'
    RECAPTCHA_SECRET_KEY = '6LchCXsrAAAAAPm9n82MxoLQXRwUucSybpFcmfEV'
else:
    RECAPTCHA_SITE_KEY = os.getenv('RECAPTCHA_SITE_KEY')
    RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY')


# ---------- Auth redirects ----------
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Allauth relaxed flags for dev/demo
DISABLE_ALLAUTH_EMAIL_VERIFICATION = True

# --- Allow YouTube video embedding (fix for CSP blocking) ---
from django.middleware.security import SecurityMiddleware

# Add or update this setting
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# Add custom response headers for embedding videos
CSP_HEADER = "frame-src https://www.youtube.com https://www.youtube-nocookie.com"

def add_csp_header(get_response):
    def middleware(request):
        response = get_response(request)
        response["Content-Security-Policy"] = CSP_HEADER
        return response
    return middleware

# Append to MIDDLEWARE if not already there
MIDDLEWARE += [
    "django.middleware.common.CommonMiddleware",
]

# Manually add this middleware in your settings
MIDDLEWARE.append("reroute_business.reroute.settings.add_csp_header")
