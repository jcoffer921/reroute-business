from django.urls import path
from . import views

# Namespaced so templates can call {% url 'dashboard:home' %}
app_name = 'dashboard'

urlpatterns = [
    # ===== Router (decides user/employer/admin) =====
    path('', views.dashboard_redirect, name='my_dashboard'),  # /dashboard/

    # ===== Role dashboards =====
    path('user/', views.user_dashboard, name='user'),
    path('employer/', views.employer_dashboard, name='employer'),
    path('admin/', views.admin_dashboard, name='admin'),
    path('admin/analytics/', views.admin_analytics_events, name='admin_analytics_events'),
    # In-site admin management pages
    path('admin/jobs/', views.admin_jobs_manage, name='admin_jobs_manage'),
    path('admin/jobs/<int:job_id>/toggle/', views.admin_job_toggle_active, name='admin_job_toggle_active'),
    path('admin/applications/', views.admin_applications_manage, name='admin_applications_manage'),
    path('admin/applications/<int:app_id>/status/', views.admin_application_update_status, name='admin_application_update_status'),
    # Admin actions for flagged jobs
    path('admin/flagged-jobs/<int:job_id>/approve/', views.approve_flagged_job, name='approve_flagged_job'),
    path('admin/flagged-jobs/<int:job_id>/remove/', views.remove_flagged_job, name='remove_flagged_job'),

    # ===== User features =====
    path('saved-jobs/', views.saved_jobs_view, name='saved_jobs'),
    path('saved-jobs/archive/', views.archive_saved_job, name='archive_saved_job'),
    path('saved-jobs/unarchive/', views.unarchive_job, name='unarchive_job'),
    path('matches/', views.matched_jobs_view, name='matched_jobs'),
    path('notifications/', views.notifications_view, name='notifications'),
    # ===== User interviews modal + actions =====
    path('user/interviews/', views.user_interviews_modal, name='user_interviews_modal'),
    path('user/interviews/accept/', views.user_accept_interview, name='user_accept_interview'),
    path('user/interviews/request-reschedule/', views.user_request_reschedule, name='user_request_reschedule'),

    # ===== Employer analytics =====
    path('employer/analytics/', views.employer_analytics, name='employer_analytics'),
    path('employer/candidates/', views.employer_candidates, name='employer_candidates'),

    # ===== Employer job management =====
    path('employer/job/<int:job_id>/toggle/', views.employer_job_toggle, name='employer_job_toggle'),
    path('employer/job/<int:job_id>/applicants/', views.job_applicants, name='job_applicants'),
    path('employer/interviews/schedule/', views.schedule_interview, name='schedule_interview'),
    path('employer/interviews/reschedule/', views.reschedule_interview, name='reschedule_interview'),
    path('employer/interviews/cancel/', views.cancel_interview, name='cancel_interview'),
    path('employer/job/<int:job_id>/matches/', views.employer_job_matches, name='employer_job_matches'),
    path('employer/matcher/', views.employer_matcher, name='employer_matcher'),
]
