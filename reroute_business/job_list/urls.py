from django.urls import path
from job_list.user import views as user_views
from job_list.employers import views as employer_views

urlpatterns = [
  # ===== USER-SIDE JOB VIEWS =====
  path('', user_views.opportunities_view, name='opportunities'),                # /jobs/
  path('<int:job_id>/', user_views.job_detail_view, name='job_detail'),         # /jobs/3/
  path('<int:job_id>/apply/', user_views.apply_to_job, name='apply_to_job'),    # /jobs/3/apply/
  path('match/<int:seeker_id>/', user_views.match_jobs, name='match_jobs'),     # /jobs/match/1/
  path('toggle-save/', user_views.toggle_saved_job, name='toggle_saved_job'),


  # ===== EMPLOYER VIEWS =====
  path('employer/dashboard/', employer_views.dashboard_view, name='employer_dashboard'),
  path('employer/job/create/', employer_views.create_job, name='create_job'),
]
