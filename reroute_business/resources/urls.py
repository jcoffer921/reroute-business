# resources/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.resource_list, name='resource_list'),
    path('directory/', views.resources_directory, name='resource_directory'),
    path('directory/<slug:slug>/', views.resource_directory_detail, name='resource_directory_detail'),
    path('module/<int:pk>/', views.module_detail, name='module_detail'),
    path('modules/<int:pk>/', views.module_detail),  # legacy alias
    path('module/<int:pk>/quiz/schema/', views.module_quiz_schema, name='module_quiz_schema'),
    path('module/<int:pk>/quiz/submit/', views.module_quiz_submit, name='module_quiz_submit'),
    path('api/modules/<int:pk>/quiz/', views.module_quiz_schema),  # legacy API alias

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

    # Interactive lessons
    path('lessons/<slug:slug>/', views.lesson_detail, name='lesson_detail'),
    path('api/lessons/<slug:slug>/schema/', views.lesson_schema, name='lesson_schema'),
    path('api/lessons/<slug:slug>/attempt/', views.lesson_attempt, name='lesson_attempt'),
    path('api/lessons/<slug:slug>/progress/', views.lesson_progress, name='lesson_progress'),
]
