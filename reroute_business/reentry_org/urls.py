from django.urls import path
from . import views

app_name = 'reentry_org'

urlpatterns = [
    path('catalog/', views.organization_catalog, name='organization_catalog'),
    path('save/', views.toggle_saved_org, name='toggle_saved_org'),
    path('applications/<int:application_id>/pdf/', views.application_pdf, name='application_pdf'),
]
