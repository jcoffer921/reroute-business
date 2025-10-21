from django.urls import path
from . import views

app_name = 'reentry_org'

urlpatterns = [
    path('catalog/', views.organization_catalog, name='organization_catalog'),
]

