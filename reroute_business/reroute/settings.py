# settings.py
import os
import ctypes.util
from pathlib import Path
from django.utils.translation import gettext_lazy as _

from dotenv import load_dotenv
load_dotenv()

import dj_database_url


def _first_existing_path(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Temporary production-safe GIS toggle.
# Keep GIS enabled by default for local/dev.
USE_GIS = os.environ.get("DISABLE_GIS") != "1"

# GeoDjango native library discovery (only when GIS is enabled).
if USE_GIS:
    # On Windows, prefer explicit env vars then known OSGeo4W paths.
    # On Linux/macOS (e.g., Render), rely on env vars or system discovery.
    if os.name == "nt":
        GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH") or _first_existing_path([
            r"C:\Users\jcoff\AppData\Local\Programs\OSGeo4W\bin\gdal312.dll",
            r"C:\OSGeo4W\bin\gdal312.dll",
            r"C:\OSGeo4W\bin\gdal311.dll",
            r"C:\OSGeo4W\bin\gdal310.dll",
            ctypes.util.find_library("gdal"),
        ])

        GEOS_LIBRARY_PATH = os.getenv("GEOS_LIBRARY_PATH") or _first_existing_path([
            r"C:\Users\jcoff\AppData\Local\Programs\OSGeo4W\bin\geos_c.dll",
            r"C:\OSGeo4W\bin\geos_c.dll",
            ctypes.util.find_library("geos_c"),
        ])
    else:
        GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH") or ctypes.util.find_library("gdal")
        GEOS_LIBRARY_PATH = os.getenv("GEOS_LIBRARY_PATH") or ctypes.util.find_library("geos_c")
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-dev-secret")

# ---------- DATABASES ----------
DB_ENGINE = "django.contrib.gis.db.backends.postgis" if USE_GIS else "django.db.backends.postgresql"
if os.getenv("DATABASE_URL"):
    _db_config = dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
    )
    _db_config["ENGINE"] = DB_ENGINE
    DATABASES = {"default": _db_config}
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": os.environ.get("DB_NAME"),
            "USER": os.environ.get("DB_USER"),
            "PASSWORD": os.environ.get("DB_PASSWORD"),
            "HOST": os.environ.get("DB_HOST"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
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
    'allauth.socialaccount.providers.google',

    # local apps
    'reroute_business.main',
    'reroute_business.benefit_finder',
    'reroute_business.resumes',
    'reroute_business.dashboard',
    'reroute_business.blog',
    'reroute_business.core',
    'reroute_business.profiles',
    'reroute_business.job_list',
    'reroute_business.resources',
    'reroute_business.reentry_org',
    'admin_portal',
]

if USE_GIS:
    INSTALLED_APPS.append('django.contrib.gis')

# ---------- SITES FRAMEWORK ----------
SITE_ID = 1



# ---------- MIDDLEWARE ----------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # must be right after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
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
# Only enforce HTTPS security controls in deployed environments.
_HTTPS_ENFORCED = (not DEBUG) and RENDER

SESSION_COOKIE_SECURE = _HTTPS_ENFORCED
CSRF_COOKIE_SECURE = _HTTPS_ENFORCED
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = _HTTPS_ENFORCED
SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")

if _HTTPS_ENFORCED:
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True


# ---------- i18n ----------
LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', _('English')),
    ('es', _('Español')),
]
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]
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

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']

SOCIALACCOUNT_ADAPTER = 'reroute_business.main.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
    }
}

SOCIALACCOUNT_LOGIN_ON_GET = True

# Allauth relaxed flags for dev/demo
DISABLE_ALLAUTH_EMAIL_VERIFICATION = True

# ---------- Early access flags ----------
EARLY_ACCESS_MODE = True
JOBS_LIVE = False

# --- Allow YouTube video embedding (fix for CSP blocking) ---
from django.middleware.security import SecurityMiddleware

# Add or update this setting
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# --- Allow YouTube video embedding (fix for CSP blocking) ---
from django.utils.deprecation import MiddlewareMixin

# Disable Cross-Origin opener blocking so YouTube embeds work correctly
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# Define a Content Security Policy that allows YouTube videos, scripts, and images
class AddCSPHeaderMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            # Allow YouTube and Google reCAPTCHA iframes
            "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://www.google.com https://recaptcha.google.com; "
            # Scripts from self, YouTube helpers, and Google reCAPTCHA
            "script-src 'self' https://www.youtube.com https://www.gstatic.com https://www.google.com https://www.gstatic.com/recaptcha; "
            # Explicit style policy (no inline styles)
            "style-src 'self' https://www.gstatic.com; "
            # Images from self, data URIs, YouTube thumbnails, and gstatic
            "img-src 'self' data: https://i.ytimg.com https://www.gstatic.com; "
            # XHR/fetch to self and Google (reCAPTCHA)
            "connect-src 'self' https://www.google.com; "
            # Media (video) from self and YouTube
            "media-src 'self' https://www.youtube.com;"
        )
        return response

# ✅ Append our custom CSP middleware at the end of the chain
MIDDLEWARE.append("reroute_business.reroute.settings.AddCSPHeaderMiddleware")

