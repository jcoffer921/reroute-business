from django.urls import path

from . import views

app_name = 'benefit_finder'

urlpatterns = [
    path('', views.wizard, name='start'),
    path('analytics/', views.track_interaction, name='analytics'),
    path('complete/', views.mark_complete, name='complete'),
]
