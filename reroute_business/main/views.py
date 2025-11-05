# main/views.py
# ======================================================================
# ReRoute (Main App) Views - Consolidated & Commented
# - User & Employer auth (login/signup/logout)
# - Dashboard(s)
# - Onboarding steps (step1–step4 + final summary)
# - Jobs list & basic skill-based matching (legacy)
# - Contact form with reCAPTCHA (optional; uses settings keys)
# - Settings page (password, email, deactivate/delete)
# - Misc pages: home, terms, privacy, resources, about
# - Password reset CBVs with custom templates
# ======================================================================

from __future__ import annotations

# -----------------------------
# Django / Stdlib Imports
# -----------------------------
import json
import logging
import traceback

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate, login, logout, views as auth_views, update_session_auth_hash
)
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_GET, require_POST

from reroute_business.job_list.models import Application
from reroute_business.main.forms import UserSignupForm
from reroute_business.resumes.models import Resume
from reroute_business.profiles.views import is_employer


# Optional dependency for contact form reCAPTCHA
# (safe if not used)
try:
    import requests
except Exception:
    requests = None

# -----------------------------
# Local Imports
# -----------------------------
from reroute_business.profiles.models import EmployerProfile, UserProfile, Subscription
from reroute_business.main.models import YouTubeVideo

# Try to import a custom password form; if unavailable, we use Django's default.
try:
    from .forms import CustomPasswordChangeForm as PasswordForm
except Exception:
    PasswordForm = PasswordChangeForm

# If you rely on a shared Skill list:
try:
    from reroute_business.core.models import Skill
except Exception:
    Skill = None  # We’ll guard usage via conditionals

# views.py

from django.shortcuts import render
import logging
from django.apps import apps

logger = logging.getLogger(__name__)

# Allauth helpers for email verification (guarded import)
try:
    from allauth.account.utils import send_email_confirmation
    from allauth.account.models import EmailAddress
except Exception:  # allauth is installed per settings, but guard anyway
    send_email_confirmation = None
    EmailAddress = None

def home(request):
    """
    Homepage:
    - Show a limited number of featured and recent posts.
    - If the 'blog' app or its table isn't available, degrade gracefully.
    """
    FEATURED_LIMIT = 3
    RECENT_LIMIT   = 6

    featured_posts = []
    recent_posts   = []

    try:
        from reroute_business.blog.models import BlogPost
        # --- Try to get the BlogPost model dynamically to avoid import-time crashes
        BlogPost = apps.get_model('blog', 'BlogPost') if apps.is_installed('blog') else None

        if BlogPost is not None:
            # Query only if model is available; this can still raise if table is missing
            featured_posts = (
                BlogPost.objects
                .filter(published=True, featured=True)
                .order_by('-created_at')[:FEATURED_LIMIT]
            )

            recent_posts = (
                BlogPost.objects
                .filter(published=True, featured=False)
                .order_by('-created_at')[:RECENT_LIMIT]
            )
        else:
            logger.warning("Blog app not installed; rendering home without blog posts.")

    except Exception as exc:
        # Log stacktrace so you can see missing table/column or other errors in Render logs
        logger.exception("Home view failed while fetching BlogPost items: %s", exc)
        # Fall back to empty lists; template will render without posts

    # ✅ Always render with safe defaults so template never crashes
    return render(request, 'main/home.html', {
        'featured_posts': featured_posts,
        'recent_posts': recent_posts,
        'FEATURED_LIMIT': FEATURED_LIMIT,
        'RECENT_LIMIT': RECENT_LIMIT,
    })


def about_us(request):
    """Public About page with lightweight page view logging."""
    # Best-effort analytics; never blocks rendering
    try:
        from reroute_business.core.utils.analytics import track_event
        track_event(event_type='page_view', request=request)
    except Exception:
        pass
    return render(request, 'main/about_us.html')


def resources_view(request):
    """Public Resources index page."""
    return render(request, 'resources/resource_list.html')


@require_GET
def pricing(request):
    """
    Pricing page with tabs for job seekers and employers.
    - Uses `?tab=user|employer` to select tab; defaults by role.
    - Passes current subscription plan (for employers) to highlight/disable CTAs.
    """
    tab = (request.GET.get('tab') or '').lower()
    if tab not in {"user", "employer"}:
        tab = "employer" if is_employer(request.user) else "user"

    current_plan = None
    if request.user.is_authenticated and is_employer(request.user):
        try:
            from reroute_business.profiles.models import Subscription
            sub, _ = Subscription.objects.get_or_create(user=request.user)
            current_plan = (sub.plan_name or '').lower()
        except Exception:
            current_plan = None

    # Render updated pricing (v2) with three primary segments
    return render(request, 'main/pricing_v2.html', {
        "active_tab": tab,
        "current_plan": current_plan,
    })


@require_GET
def faq_view(request):
    """Frequently Asked Questions page with accordion layout."""
    return render(request, 'main/faq.html')


@require_GET
def pricing_checkout(request):
    """
    Placeholder checkout page for employer plans.
    - If not authenticated: redirect to employer login with next back to this checkout URL.
    - If authenticated but not employer: send to employer signup with next.
    - Otherwise: render a non-functional checkout preview (no billing yet).
    """
    plan = (request.GET.get('plan') or '').lower()
    PLAN_META = {
        'basic': {
            'name': 'Basic',
            'price': '$50 / month',
            'per_hire': '+ $1,000 per hire',
            'features': [
                'For small employers testing ReRoute or hiring occasionally.',
                'Up to 5 job postings / month',
                'Limited candidate database access (basic profiles, no direct contact until candidate applies)',
                'Standard analytics (views & applicants per job)',
                'Standard listings (no company logo / no featured placement)',
                'Email support only',
                '❌ No interview scheduling',
                '❌ No integrations',
            ],
        },
        'pro': {
            'name': 'Pro',
            'price': '$99 / month',
            'per_hire': '+ $500 per hire',
            'features': [
                'For active employers who want to hire faster.',
                'Unlimited job postings',
                'Full candidate database access (advanced search + contact details)',
                'Advanced analytics (conversion tracking, hire reports, trends)',
                'Company logo + featured listings',
                'Priority support (faster response times)',
                '✅ Interview scheduling built-in',
                '✅ Basic integrations (CSV export / ATS import)',
            ],
        },
    }

    if plan not in PLAN_META:
        messages.error(request, 'Unknown or unsupported plan.')
        return redirect(reverse('pricing') + '?tab=employer')

    checkout_url = f"{reverse('checkout')}?plan={plan}"

    if not request.user.is_authenticated:
        # Route to employer login with return back to checkout
        return redirect(f"{reverse('employer_login')}?next={checkout_url}")

    if not is_employer(request.user):
        # Ask them to create an employer account, then return here
        messages.info(request, 'Please create an employer account to continue.')
        return redirect(f"{reverse('employer_signup')}?next={checkout_url}")

    meta = PLAN_META[plan]
    return render(request, 'main/pricing_checkout.html', {
        'plan_key': plan,
        'plan_name': meta['name'],
        'plan_price': meta['price'],
        'plan_per_hire': meta['per_hire'],
        'plan_features': meta.get('features', []),
    })


def opportunities_view(request):
    """
    Public-facing job search page (filters + results).
    If your template path is different, update it here.
    """
    return render(request, 'job_list/opportunities.html')


def terms_view(request):
    """Legal: Terms & Conditions."""
    return render(request, 'legal/terms_and_conditions.html')


def privacy_view(request):
    """Legal: Privacy Policy."""
    return render(request, 'legal/privacy_policy.html')

# =========================================================================
# Contact Page w/ reCAPTCHA (optional)
# =========================================================================

def contact_view(request):
    """
    Contact form that validates Google reCAPTCHA v2/v3.
    Expects these in settings:
      - RECAPTCHA_SITE_KEY
      - RECAPTCHA_SECRET_KEY
      - CONTACT_RECEIVER_EMAIL
      - DEFAULT_FROM_EMAIL
    Template: main/contact_us.html (must render the site key on the page)
    """
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        organization = request.POST.get('organization')
        interest = request.POST.get('interest')
        message = request.POST.get('message')
        recaptcha_token = request.POST.get('g-recaptcha-response')

        # Verify reCAPTCHA if available/configured
        if requests and getattr(settings, 'RECAPTCHA_SECRET_KEY', None):
            try:
                resp = requests.post(
                    'https://www.google.com/recaptcha/api/siteverify',
                    data={'secret': settings.RECAPTCHA_SECRET_KEY, 'response': recaptcha_token},
                    timeout=6,
                ).json()
            except Exception as e:
                logger.warning(f"reCAPTCHA call failed: {e}")
                resp = {'success': False}

            if not resp.get('success'):
                messages.error(request, "reCAPTCHA verification failed. Please try again.")
                return redirect('contact')

        # Send email
        try:
            from django.core.mail import send_mail

            subject = f"New Contact Form Submission: {interest or 'General Inquiry'}"
            body = (
                f"Name: {first_name} {last_name}\n"
                f"Email: {email}\n"
                f"Phone: {phone or 'N/A'}\n"
                f"Organization: {organization or 'N/A'}\n"
                f"Interested in: {interest or 'N/A'}\n\n"
                f"Message:\n{message}"
            )
            send_mail(
                subject,
                body,
                getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                [getattr(settings, 'CONTACT_RECEIVER_EMAIL', '')],
                fail_silently=False,
            )
            messages.success(request, "Thanks for reaching out — we'll be in touch soon.")
            return redirect('contact')

        except Exception as e:
            logger.error(f"Contact email failed: {e}")
            messages.error(request, "Something went wrong. Please try again.")

    return render(request, 'main/contact_us.html', {
        'recaptcha_site_key': getattr(settings, 'RECAPTCHA_SITE_KEY', None)
    })

# =========================================================================
# Auth: USER Signup/Login/Logout
# =========================================================================

def signup_view(request):
    """
    Regular user signup.
    - Uses UserSignupForm (validates email uniqueness & password strength).
    - Logs in the user on success and redirects to dashboard (or ?next=).
    """
    # Bind POST data if present so errors re-render on the page
    user_form = UserSignupForm(request.POST or None)

    if request.method == 'POST':
        try:
            if user_form.is_valid():
                # Create the user account
                user = user_form.save()

                # Send verification email via allauth and show confirmation screen
                if send_email_confirmation is not None:
                    try:
                        send_email_confirmation(request, user)
                    except Exception:
                        logger.exception("Failed to send verification email for user signup")

                return render(request, 'main/verification_sent.html', {
                    'email': user.email,
                    'is_employer': False,
                })

            # Log validation errors to server logs (won't crash now)
            logger.info("Signup validation errors: %s", user_form.errors)
        except Exception as e:
            # Log full traceback to server logs and fall through to re-render
            logger.exception("Signup exception: %s", e)

    return render(request, 'main/signup.html', {'user_form': user_form})


@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Unified user login:
      - GET: render login page
      - POST (JSON): {username/email, password, next?} -> JSON
      - POST (form): username/email + password -> redirect or re-render with error
    """

    # ---------- GET: show page ----------
    if request.method == "GET":
        return render(request, "main/login.html")

    # ---------- Helper: auth by username OR email ----------
    def auth_user(identifier: str, password: str):
        # Normalize
        identifier = (identifier or "").strip()
        password = password or ""
    
        if not identifier or not password:
            return None, "Username/email and password are required."

        # Resolve email -> username if needed (case-insensitive)
        u = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
        username = u.username if u else identifier

        # Authenticate
        user = authenticate(request, username=username, password=password)
        if not user:
            return None, "Invalid credentials"
        if not user.is_active:
            return None, "This account is inactive."
        return user, None

    # ---------- Helper: compute safe redirect ----------
    def safe_dest(user, requested_next: str | None):
        """
        Prefer a safe ?next= when present; otherwise choose by role.
        Admin > Employer > User.
        """
        # 1) Safe-guard ?next=
        if requested_next and url_has_allowed_host_and_scheme(
            requested_next, allowed_hosts={request.get_host()}
        ):
            return requested_next

        # 2) Role-aware defaults (namespaced dashboard)
        try:
            if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
                return reverse('dashboard:admin')
            if is_employer(user):
                return reverse('dashboard:employer')
            return reverse('dashboard:user')
        except NoReverseMatch:
            # Fallback paths
            if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
                return '/dashboard/admin/'
            return '/dashboard/employer/' if is_employer(user) else '/dashboard/user/'

    # ---------- Branch by content type ----------
    content_type = (request.headers.get("Content-Type") or "").split(";")[0].strip()

    # A) JSON/AJAX
    if content_type == "application/json":
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"status": "fail", "message": "Invalid JSON"}, status=400)

        identifier = data.get("username") or data.get("email") or ""
        password   = data.get("password") or ""
        requested_next = data.get("next")  # may be None
        remember_raw   = data.get("remember")
        remember_me    = (
            (remember_raw is True)
            or str(remember_raw).lower() in {"1", "true", "yes", "on"}
        )

        user, err = auth_user(identifier, password)
        if err:
            code = 401 if err == "Invalid credentials" else 400
            return JsonResponse({"status": "fail", "message": err}, status=code)

        # Require verified email before login (can be disabled via settings flag)
        from django.conf import settings as django_settings
        if not getattr(django_settings, 'DISABLE_ALLAUTH_EMAIL_VERIFICATION', True):
            if EmailAddress is not None:
                try:
                    is_verified = EmailAddress.objects.filter(user=user, verified=True).exists()
                except Exception:
                    is_verified = True
                if not is_verified:
                    if send_email_confirmation is not None:
                        try:
                            send_email_confirmation(request, user)
                        except Exception:
                            logger.exception("Failed to resend verification email during login")
                    return JsonResponse({
                        "status": "fail",
                        "message": "Please verify your email. We just sent a new link.",
                    }, status=403)

        login(request, user)
        # Session persistence based on Remember checkbox
        try:
            request.session.set_expiry(60 * 60 * 24 * 30 if remember_me else 0)
        except Exception:
            pass
        return JsonResponse({
            "status": "success",
            "redirect": safe_dest(user, requested_next),  # ✅ role-aware & safe
        })

    # B) Classic form (treat blank/unknown CT as form too)
    if content_type in ("application/x-www-form-urlencoded", "multipart/form-data", ""):
        identifier     = request.POST.get("username") or request.POST.get("email") or ""
        password       = request.POST.get("password") or ""
        requested_next = request.POST.get("next")  # may be None
        remember_me    = (request.POST.get("remember") in ("1", "true", "on"))

        user, err = auth_user(identifier, password)
        if err:
            # Re-render with inline error
            return render(request, "main/login.html", {
                "error": err,
                "prefill_identifier": identifier,
                "next": requested_next,  # keep it if present
            }, status=401 if err == "Invalid credentials" else 400)

        # Require verified email before login (can be disabled via settings flag)
        from django.conf import settings as django_settings
        if not getattr(django_settings, 'DISABLE_ALLAUTH_EMAIL_VERIFICATION', True):
            if EmailAddress is not None:
                try:
                    is_verified = EmailAddress.objects.filter(user=user, verified=True).exists()
                except Exception:
                    is_verified = True
                if not is_verified:
                    if send_email_confirmation is not None:
                        try:
                            send_email_confirmation(request, user)
                        except Exception:
                            logger.exception("Failed to resend verification email during login")
                    return render(request, "main/login.html", {
                        "error": "Please verify your email. We just sent a new link.",
                        "prefill_identifier": identifier,
                        "next": requested_next,
                    }, status=403)

        login(request, user)
        # Session persistence based on Remember checkbox
        try:
            request.session.set_expiry(60 * 60 * 24 * 30 if remember_me else 0)
        except Exception:
            pass
        return redirect(safe_dest(user, requested_next))

    # C) Anything else → 400
    return HttpResponseBadRequest("Unsupported Content-Type for POST.")

def logout_view(request):
    """Log out anyone (user or employer) and bounce to login."""
    logout(request)
    return redirect('login')

# ===============================
# Video Library
# ===============================
def video_gallery(request):
    videos = YouTubeVideo.objects.all().order_by('-created_at')
    return render(request, 'main/video_gallery.html', {
        'videos': videos,
    })

# =========================================================================
# Email Verification Helpers
# =========================================================================

@login_required
@require_http_methods(["GET", "POST"])
def verify_email_notice(request):
    """
    For logged-in users who are not verified. Shows a reminder and lets them
    resend the verification email.
    """
    sent = False
    if request.method == 'POST' and send_email_confirmation is not None:
        try:
            send_email_confirmation(request, request.user)
            sent = True
            messages.success(request, "Verification email sent. Please check your inbox.")
        except Exception:
            logger.exception("Failed to send verification email from verify_email_notice")
            messages.error(request, "We couldn't send the verification email right now. Please try again soon.")
    return render(request, 'main/verify_email.html', {
        'email': request.user.email,
        'sent': sent,
    })


@require_http_methods(["GET", "POST"])
def resend_verification_view(request):
    """
    For users not logged in who want to request a verification email again.
    Does not reveal whether the email exists.
    """
    sent = False
    if request.method == 'POST' and send_email_confirmation is not None:
        email = (request.POST.get('email') or '').strip().lower()
        if email:
            try:
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    send_email_confirmation(request, user)
                sent = True
            except Exception:
                logger.exception("Failed resend_verification for %s", email)
                # Still respond the same to avoid enumeration
                sent = True
        else:
            messages.error(request, "Please enter a valid email address.")
    return render(request, 'main/resend_verification.html', {'sent': sent})

# =========================================================================
# Auth: EMPLOYER Signup/Login & Dashboard
# =========================================================================

def _unique_username_from_email(email: str) -> str:
    """
    Generate a unique username from email local-part, e.g., "acme" -> "acme", "acme1", ...
    Keeps it readable and avoids a second form field.
    """
    base = slugify((email or "").split("@")[0]) or "user"
    username = base
    i = 1
    while User.objects.filter(username__iexact=username).exists():
        i += 1
        username = f"{base}{i}"
    return username

def _safe_redirect(default_name: str, default_path: str = "/"):
    try:
        return reverse(default_name)
    except NoReverseMatch:
        return default_path

@csrf_protect
@require_http_methods(["GET", "POST"])
def employer_signup_view(request):
    """
    Create an employer account + company profile.
    - Requires: first_name, last_name, email, password1, password2, company_name
    - Optional: website, description
    - Side effects: creates EmployerProfile, adds Employer group, logs in user
    """
    if request.method == "GET":
        return render(request, "main/employer_signup.html")

    # ---- Collect fields from POST ----
    first_name   = (request.POST.get("first_name") or "").strip()
    last_name    = (request.POST.get("last_name") or "").strip()
    email        = (request.POST.get("email") or "").strip().lower()
    password1    = request.POST.get("password1") or ""
    password2    = request.POST.get("password2") or ""
    company_name = (request.POST.get("company_name") or "").strip()
    website      = (request.POST.get("website") or "").strip()
    description  = (request.POST.get("description") or "").strip()
    agree        = request.POST.get("agree_terms") == "1"

    # ---- Basic validation ----
    errors = {}
    if not first_name:   errors["first_name"] = "First name is required."
    if not last_name:    errors["last_name"] = "Last name is required."
    if not email:        errors["email"] = "Email is required."
    if not company_name: errors["company_name"] = "Company name is required."
    if not password1:    errors["password1"] = "Password is required."
    if password1 and password1 != password2:
        errors["password2"] = "Passwords do not match."
    if not agree:
        errors["agree_terms"] = "You must agree to the Terms and Privacy Policy."

    # Uniqueness checks (email unique; username auto-generated later)
    if email and User.objects.filter(email__iexact=email).exists():
        errors["email"] = "An account with this email already exists."

    # Password validation (Django’s built-in validators)
    if password1 and password1 == password2:
        try:
            validate_password(password1)
        except ValidationError as ve:
            errors["password1"] = " ".join(ve.messages)

    if errors:
        # Re-render with inline field errors and keep safe prefill values
        return render(request, "main/employer_signup.html", {
            "errors": errors,
            "prefill": {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "company_name": company_name,
                "website": website,
                "description": description,
            }
        }, status=400)

    # ---- Create user + employer profile ----
    username = _unique_username_from_email(email)
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password1,
        first_name=first_name,
        last_name=last_name,
    )

    # Create EmployerProfile (signals aren’t needed here)
    EmployerProfile.objects.create(
        user=user,
        company_name=company_name,
        website=website,
        description=description,
    )

    # Optional: add to Employer group so permissions stay tidy
    try:
        employer_group, _ = Group.objects.get_or_create(name="Employer")
        user.groups.add(employer_group)
    except Exception:
        # Don’t block signup on group issues
        pass

    # Send verification email (no auto-login)
    if send_email_confirmation is not None:
        try:
            send_email_confirmation(request, user)
        except Exception:
            logger.exception("Failed to send verification email for employer signup")

    return render(request, 'main/verification_sent.html', {
        'email': user.email,
        'is_employer': True,
    })


@csrf_protect
@require_http_methods(["GET", "POST"])
def employer_login_view(request):
    """
    Employer-only login that supports JSON + classic form.
    - Auth by username OR email (case-insensitive)
    - Requires 'is_employer(user)' (EmployerProfile OR Employer group)
    - Honors ?next= only if safe; otherwise goes to employer dashboard
    """

    # --- helpers (same as you have) ---
    def auth_employer(identifier: str, password: str):
        identifier = (identifier or "").strip()
        password = password or ""
        if not identifier or not password:
            return None, "Username/email and password are required."

        u = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
        username_for_auth = u.username if u else identifier

        user = authenticate(request, username=username_for_auth, password=password)
        if not user:
            return None, "Invalid credentials"
        if not user.is_active:
            return None, "This account is inactive."
        if not is_employer(user):  # EmployerProfile OR Employer group
            return None, "This account is not an employer."
        return user, None

    def safe_dest_employer(requested_next):
        if requested_next and url_has_allowed_host_and_scheme(requested_next, {request.get_host()}):
            return requested_next
        try:
            return reverse("dashboard:employer")
        except NoReverseMatch:
            return "/dashboard/employer/"

    # --- Branch: try JSON first; otherwise treat as form ---
    ctype = (request.headers.get("Content-Type") or "").split(";")[0].strip()
    is_json = ctype == "application/json"

    if is_json:
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            # 👇 Fallback to form-style handling instead of 400
            is_json = False

    if is_json:
        identifier     = (data.get("username") or data.get("email") or "").strip()
        password       = data.get("password") or ""
        requested_next = data.get("next")
        remember_raw   = data.get("remember")
        remember_me    = bool(remember_raw) in (True,) or str(remember_raw).lower() in {"1","true","yes","on"}

        user, err = auth_employer(identifier, password)
        if err:
            code = 401 if err == "Invalid credentials" else (403 if err == "This account is not an employer." else 400)
            return JsonResponse({"status": "fail", "message": err}, status=code)

        # Require verified email before employer login (can be disabled via settings flag)
        from django.conf import settings as django_settings
        if not getattr(django_settings, 'DISABLE_ALLAUTH_EMAIL_VERIFICATION', True):
            if EmailAddress is not None:
                try:
                    is_verified = EmailAddress.objects.filter(user=user, verified=True).exists()
                except Exception:
                    is_verified = True
                if not is_verified:
                    if send_email_confirmation is not None:
                        try:
                            send_email_confirmation(request, user)
                        except Exception:
                            logger.exception("Failed to resend verification email (employer login)")
                    return JsonResponse({
                        "status": "fail",
                        "message": "Please verify your email. We just sent a new link.",
                    }, status=403)

        login(request, user)
        # Session persistence based on Remember checkbox
        try:
            request.session.set_expiry(60 * 60 * 24 * 30 if remember_me else 0)
        except Exception:
            pass
        return JsonResponse({"status": "success", "redirect": safe_dest_employer(requested_next)})

    # --- Form (or unknown content-type): never 400 here ---
    identifier     = request.POST.get("username") or request.POST.get("email") or ""
    password       = request.POST.get("password") or ""
    requested_next = request.POST.get("next")
    remember_me    = (request.POST.get("remember") in ("1", "true", "on"))

    user, err = auth_employer(identifier, password)
    if err:
        return render(request, "main/employer_login.html", {
            "error": err,
            "prefill_identifier": identifier,
        })

    # Require verified email before employer login (can be disabled via settings flag)
    from django.conf import settings as django_settings
    if not getattr(django_settings, 'DISABLE_ALLAUTH_EMAIL_VERIFICATION', True):
        if EmailAddress is not None:
            try:
                is_verified = EmailAddress.objects.filter(user=user, verified=True).exists()
            except Exception:
                is_verified = True
            if not is_verified:
                if send_email_confirmation is not None:
                    try:
                        send_email_confirmation(request, user)
                    except Exception:
                        logger.exception("Failed to resend verification email (employer login)")
                return render(request, "main/employer_login.html", {
                    "error": "Please verify your email. We just sent a new link.",
                    "prefill_identifier": identifier,
                }, status=403)

    login(request, user)
    # Session persistence based on Remember checkbox
    try:
        request.session.set_expiry(60 * 60 * 24 * 30 if remember_me else 0)
    except Exception:
        pass
    return redirect(safe_dest_employer(requested_next))

@login_required
def employer_dashboard_view(request):
    """
    Basic employer dashboard gate:
    - Only members of 'Employer' group can enter
    Template: employers/dashboard.html
    """
    if not request.user.groups.filter(name='Employer').exists():
        return HttpResponseForbidden("Access denied: Employers only.")
    return render(request, 'dashboard/employer_dashboard.html')


# =========================================================================
# User Dashboard + Settings
# =========================================================================

def dashboard(request):
    """
    Simple user dashboard view.
    Template: dashboard/user_dashboard.html
    """
    return render(request, 'dashboard/user_dashboard.html')


@login_required
def dashboard_view(request):
    """
    If another part of the code imports `dashboard_view`, keep this for compatibility.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    resume = Resume.objects.filter(user=request.user).first()
    applications = Application.objects.filter(applicant=request.user)

    return render(request, 'user_dashboard.html', {
        'profile': profile,
        'resume': resume,
        'applications': applications,
    })


@login_required
def settings_view(request):
    """
    Unified settings screen for:
    - Change password (uses CustomPasswordChangeForm if present)
    - Update email
    - Deactivate or delete account
    Template: main/settings.html
    """
    password_form = PasswordForm(request.user)
    # Ensure profile exists for preferences section
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Account preferences form (username, display name, status)
    from .forms import AccountPreferencesForm, RecoveryOptionsForm
    initial_prefs = {
        'username': request.user.username,
        'display_name': getattr(profile, 'preferred_name', '') or '',
        'status': getattr(profile, 'status', '') or '',
    }
    account_prefs_form = AccountPreferencesForm(user=request.user, initial=initial_prefs)
    # Recovery options form (backup contact)
    recovery_initial = {
        'backup_email': profile.personal_email or '',
        'backup_phone': profile.phone_number or '',
    }
    recovery_form = RecoveryOptionsForm(user=request.user, initial=recovery_initial)

    if request.method == 'POST':
        # Change Password
        if 'change_password' in request.POST:
            password_form = PasswordForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
                return redirect('settings')

        # Update Email
        elif 'update_email' in request.POST:
            new_email = request.POST.get('email')
            if new_email:
                request.user.email = new_email
                request.user.save()
                messages.success(request, "Email updated successfully.")
                return redirect('settings')

        # Update account preferences (username, display name, status)
        elif 'update_account_prefs' in request.POST:
            account_prefs_form = AccountPreferencesForm(request.POST, user=request.user)
            if account_prefs_form.is_valid():
                new_username = account_prefs_form.cleaned_data['username']
                display_name = account_prefs_form.cleaned_data.get('display_name', '')
                status = account_prefs_form.cleaned_data.get('status', '')

                # Apply to models
                if new_username and new_username != request.user.username:
                    request.user.username = new_username
                    request.user.save(update_fields=["username"])

                profile.preferred_name = display_name
                profile.status = status
                try:
                    profile.save(update_fields=["preferred_name", "status"])
                except Exception:
                    profile.save()

                messages.success(request, "Account preferences updated.")
                return redirect('settings')

        # Update recovery options (backup email/phone)
        elif 'update_recovery' in request.POST:
            recovery_form = RecoveryOptionsForm(request.POST, user=request.user)
            if recovery_form.is_valid():
                profile.personal_email = recovery_form.cleaned_data.get('backup_email', '')
                profile.phone_number = recovery_form.cleaned_data.get('backup_phone', '')
                try:
                    profile.save(update_fields=["personal_email", "phone_number"])
                except Exception:
                    profile.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'ok': True})
                messages.success(request, "Recovery options saved.")
                return redirect('settings')

        # Deactivate
        elif 'deactivate_account' in request.POST:
            request.user.is_active = False
            request.user.save()
            messages.warning(request, "Account deactivated. You've been logged out.")
            return redirect('logout')

        # Delete
        elif 'delete_account' in request.POST:
            request.user.delete()
            messages.error(request, "Your account has been permanently deleted.")
            return redirect('home')

    # Build subscription context for the Subscription card
    sub, _ = Subscription.objects.get_or_create(user=request.user)
    employer = is_employer(request.user)

    # Non-employers should always be on Free (enforce softly here as well)
    if not employer and sub.plan_name != Subscription.PLAN_FREE:
        sub.plan_name = Subscription.PLAN_FREE
        sub.active = True
        sub.expiry_date = None
        try:
            sub.save(update_fields=["plan_name", "active", "expiry_date"])
        except Exception:
            pass

    # Determine email verification; can be disabled for testing
    is_verified = True
    try:
        from django.conf import settings as django_settings
        if not getattr(django_settings, 'DISABLE_ALLAUTH_EMAIL_VERIFICATION', True):
            if EmailAddress is not None:
                is_verified = EmailAddress.objects.filter(user=request.user, verified=True).exists()
    except Exception:
        is_verified = True

    # Pricing URL with correct tab
    try:
        if employer:
            subscription_pricing_url = reverse('pricing') + '?tab=employer'
        else:
            subscription_pricing_url = reverse('pricing') + '?tab=user'
    except Exception:
        subscription_pricing_url = '/'

    return render(request, 'main/settings.html', {
        'password_form': password_form,
        'account_prefs_form': account_prefs_form,
        'recovery_form': recovery_form,
        'subscription': sub,
        'is_employer': employer,
        'is_verified': is_verified,
        'subscription_pricing_url': subscription_pricing_url,
    })

# =========================================================================
# Resume Helpers
# =========================================================================

def create_resume_redirect(request):
    """
    Temporary redirect into your resumes app flow.
    Update the namespace/path if needed.
    """
    return redirect('resumes:resume_contact_info')

def resume_preview(request, resume_id: int):
    """
    Render a resume by template selection stored on the model.
    NOTE: This assumes `Resume` has a `template` field. If not, adjust accordingly.
    """
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    template_name = f"resumes/templates/{getattr(resume, 'template', '')}.html" if getattr(resume, 'template', None) else "resumes/templates/simple.html"
    return render(request, template_name, {'resume': resume})

def get_skills_json(request):
    """
    Returns a JSON list of skill names from the `core.Skill` model.
    If `core` app isn’t available, returns an empty list.
    """
    if Skill is None:
        return JsonResponse([], safe=False)
    skills = list(Skill.objects.values_list('name', flat=True))
    return JsonResponse(skills, safe=False)

# =========================================================================
# Password Reset (Custom Templates)
# =========================================================================

class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception as exc:
            # Log and still redirect to done page so users aren't blocked
            logging.getLogger(__name__).exception("Password reset email failed: %s", exc)
            messages.warning(self.request, "We couldn't send the email right now, but if the address exists, the link will arrive shortly.")
            return redirect(self.get_success_url())


class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'


class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'


# =========================================================================
# Dev-only Utilities
# =========================================================================

def dev_auto_login_user(request):
    """
    TEMP: Automatically logs in a hardcoded regular user.
    Use ONLY for development testing.
    """
    user = authenticate(username='testuser', password='TestPass123!')
    if user:
        login(request, user)
        return redirect('dashboard')
    return redirect('login')


def dev_create_test_user():
    """
    Creates a hardcoded user account for development.
    Includes group assignment for "User".
    """
    print("🔍 Creating test user account...")

    user_group, created = Group.objects.get_or_create(name='User')
    if created:
        print(f"✅ User group created (ID: {user_group.id})")
    else:
        print("ℹ️ User group already exists.")

    if User.objects.filter(username='testuser').exists():
        user = User.objects.get(username='testuser')
        print("ℹ️ Test user already exists.")
    else:
        user = User.objects.create_user(
            username='testuser',
            email='user@example.com',
            password='TestPass123!'
        )
        user.first_name = "Test"
        user.last_name = "User"
        user.save()
        print("✅ Test user created.")

    if not user.groups.filter(name='User').exists():
        user.groups.add(user_group)
        print("✅ User group assigned.")
    else:
        print("ℹ️ User already in group.")

    print("🎯 Test user account ready.")

def dev_auto_login_employer(request):
    """
    TEMP: Automatically logs in a hardcoded employer.
    Use ONLY for development testing.
    """
    employer = authenticate(username='testemployer', password='TestPass123!')
    if employer:
        login(request, employer)
        return redirect('/employer/dashboard/')
    return redirect('employer_login')


def dev_create_test_employer():
    """
    Creates a hardcoded employer account for development.
    Includes group assignment for "Employer".
    """
    print("🔍 Creating test employer account...")

    employer_group, created = Group.objects.get_or_create(name='Employer')
    if created:
        print(f"✅ Employer group created (ID: {employer_group.id})")
    else:
        print("ℹ️ Employer group already exists.")

    if User.objects.filter(username='testemployer').exists():
        employer_user = User.objects.get(username='testemployer')
        print("ℹ️ Test employer already exists.")
    else:
        employer_user = User.objects.create_user(
            username='testemployer',
            email='employer@example.com',
            password='TestPass123!'
        )
        employer_user.first_name = "Test"
        employer_user.last_name = "Employer"
        employer_user.save()
        print("✅ Test employer created.")

    if not employer_user.groups.filter(name='Employer').exists():
        employer_user.groups.add(employer_group)
        print("✅ Employer group assigned.")
    else:
        print("ℹ️ Employer already in group.")

    print("🎯 Test employer account ready.")
