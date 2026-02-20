from django.urls import path

from . import views

app_name = 'benefit_finder'

urlpatterns = [
    path('', views.wizard, name='start'),
]
