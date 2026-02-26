# main/urls.py
from django.urls import include, path
from django.shortcuts import redirect
from . import views
from reroute_business.job_list.user import views as user_views
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
    path('welcome/', views.welcome, name='welcome'),
    path('for-agencies/', views.for_agencies, name='for_agencies'),
    path('for-agencies/apply/', views.for_agencies_apply, name='for_agencies_apply'),
    path('for-agencies/thank-you/', views.for_agencies_thank_you, name='for_agencies_thank_you'),
    path('start/', views.early_access_cta, name='early_access_cta'),
    path('about-us/', views.about_us, name='about_us'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('contact/', views.contact_view, name='contact'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/accessibility/', views.accessibility_settings_view, name='settings_accessibility'),
    path('resources/', views.resources_view, name='resources'),
    path('pricing/', views.pricing, name='pricing'),
    path('pricing/checkout/', views.pricing_checkout, name='checkout'),
    path('faq/', views.faq_view, name='faq'),
    path('benefit-finder/', include(('reroute_business.benefit_finder.urls', 'benefit_finder'), namespace='benefit_finder')),

    # ================ Email Verification Helpers ================
    path('verify-email/', views.verify_email_notice, name='verify_email_notice'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),

    # ================ Employer Auth & Dashboard ================
    path('employer/login/', views.employer_login_view, name='employer_login'),
    path('employer/signup/', views.employer_signup_view, name='employer_signup'),
    path('employer/onboarding/', views.employer_oauth_onboarding_view, name='employer_oauth_onboarding'),
    # Legacy employer dashboard path → redirect to dashboard app
    path('employer/dashboard/', lambda request: redirect('dashboard:employer'), name='employer_dashboard'),
    path('accounts/role-redirect/', views.oauth_role_redirect, name='oauth_role_redirect'),

    # ================ User-side Job Board (prefixed) ================
    path('opportunities/', user_views.opportunities_view, name='opportunities'),
    path('opportunities/<int:job_id>/', user_views.job_detail_view, name='job_detail'),
    path('opportunities/<int:job_id>/apply/', user_views.apply_to_job, name='apply_to_job'),

    # (Optional) keep this if referenced elsewhere
    path('match/<int:seeker_id>/', user_views.match_jobs, name='match_jobs'),

    # ================ Profile Onboarding Redirect ================
    path('profile/step1/', lambda request: redirect('resumes:resume_basics_step')),

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
    path('videos/', views.video_gallery, name='video_gallery'),
    path('videos/<int:pk>/', views.video_watch, name='video_watch'),
]
