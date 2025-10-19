# resources/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.resource_list, name='resource_list'),

    # Job tools resources
    path('job-tools/', views.job_tools_index, name='job_tools_index'),
    path('job-tools/interview-prep/', views.interview_prep, name='interview_prep'),
    path('job-tools/email-guidance/', views.email_guidance, name='email_guidance'),
    path('job-tools/tech-courses/', views.tech_courses, name='tech_courses'),

    # Reentry help resources
    path('reentry-help/', views.reentry_help_index, name='reentry_help_index'),
    path('reentry-help/legal-aid/', views.legal_aid, name='legal_aid'),
    path('reentry-help/housing/', views.housing, name='housing'),
    path('reentry-help/counseling/', views.counseling, name='counseling'),

]
