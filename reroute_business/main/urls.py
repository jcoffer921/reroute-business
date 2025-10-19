# main/urls.py
from django.urls import path, include
from django.shortcuts import redirect
from . import views
from job_list.user import views as user_views
from .forms import Step1Form, Step2Form, Step3Form, Step4Form
from .views import (
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView,
)

urlpatterns = [
    # ================= Core Pages =================
    path('', views.home, name='home'),
    path('about-us/', views.about_us, name='about_us'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('contact/', views.contact_view, name='contact'),
    path('settings/', views.settings_view, name='settings'),
    path('resources/', views.resources_view, name='resources'),
    path('pricing/', views.pricing, name='pricing'),
    path('pricing/checkout/', views.pricing_checkout, name='checkout'),

    # ================ Email Verification Helpers ================
    path('verify-email/', views.verify_email_notice, name='verify_email_notice'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),

    # ================ Employer Auth & Dashboard ================
    path('employer/login/', views.employer_login_view, name='employer_login'),
    path('employer/signup/', views.employer_signup_view, name='employer_signup'),
    # Legacy employer dashboard path → redirect to dashboard app
    path('employer/dashboard/', lambda request: redirect('dashboard:employer'), name='employer_dashboard'),

    # ================ Apps ================
    path('blog/', include('blog.urls')),
    path('resumes/', include('resumes.urls')),
    path('profile/', include('profiles.urls')),     # includes user_profile route
    path('dashboard/', include(('dashboard.urls', 'dashboard'), namespace='dashboard')),

    # ================ User-side Job Board (prefixed) ================
    path('opportunities/', user_views.opportunities_view, name='opportunities'),
    path('opportunities/<int:job_id>/', user_views.job_detail_view, name='job_detail'),
    path('opportunities/<int:job_id>/apply/', user_views.apply_to_job, name='apply_to_job'),

    # (Optional) keep this if referenced elsewhere
    path('match/<int:seeker_id>/', user_views.match_jobs, name='match_jobs'),

    # ================ Profile Onboarding Redirect ================
    path('profile/step1/', lambda request: redirect('resumes:resume_contact_info')),

    # ================ APIs ================
    path('api/skills/', views.get_skills_json, name='get_skills_json'),

    # ================ Password Reset Flow ================
    path('accounts/password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # ================ Legal ================
    path('terms/', views.terms_view, name='terms'),
    path('privacy/', views.privacy_view, name='privacy'),
]
