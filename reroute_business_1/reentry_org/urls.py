from django.urls import path
from . import views

urlpatterns = [
    path('catalog/', views.organization_catalog, name='organization_catalog'),
    path('<int:pk>/', views.organization_detail, name='organization_detail'),
]
