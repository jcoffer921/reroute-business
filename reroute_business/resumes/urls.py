# urls.py
from django.urls import path
from . import views

app_name = 'resumes'

urlpatterns = [
    # Welcome / entry
    path('welcome/', views.resume_welcome, name='resume_welcome'),
    path('create/', views.create_resume, name='create_resume'),

    # Builder steps
    path('build/contact/', views.contact_info_step, name='resume_contact_info'),
    path('build/education/', views.education_step, name='resume_education_step'),
    path('build/experience/', views.experience_step, name='resume_experience_step'),
    path('build/skills/', views.skills_step, name='resume_skills_step'),
    path('build/preview/', views.resume_preview, name='resume_preview_step'),

    # Created resume details + save
    path('created/<int:resume_id>/', views.created_resume_view, name='created_resume_view'),
    path('save/<int:resume_id>/', views.save_created_resume, name='save_created_resume'),
    path('set-template/<int:resume_id>/', views.set_resume_template, name='set_resume_template'),

    # Imported resume flow
    path('import/', views.resume_upload_page, name='resume_upload_page'),
    path('import/<int:resume_id>/', views.resume_import, name='imported_resume'),
    path('import/<int:resume_id>/update/', views.update_imported_resume, name='update_imported_resume'),
    path('import/<int:resume_id>/discard/', views.discard_imported_resume, name='discard_imported_resume'),
    path('parse-upload/', views.parse_resume_upload, name='parse_resume_upload'),
    path('upload-only/', views.upload_resume_only, name='upload_resume_only'),

    # Preview + download by id
    path('<int:resume_id>/preview/', views.resume_preview, name='resume_preview'),
    path('<int:resume_id>/download/', views.download_resume, name='download_resume'),
    path('preview-style/<int:resume_id>/', views.preview_style, name='preview_style'),

    # Employer-accessible read-only views by candidate username
    path('employer/view/<str:username>/', views.employer_preview_resume, name='employer_view_resume'),
    path('employer/download/<str:username>/', views.employer_download_resume, name='employer_download_resume'),

    # Misc
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
]
