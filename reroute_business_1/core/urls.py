from django.urls import path
from . import views

urlpatterns = [
    path('skills/', views.suggested_skills, name='suggested_skills'),
]