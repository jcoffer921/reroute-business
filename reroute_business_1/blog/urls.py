from django.urls import path
from .views import blog_detail, blog_category, blog_list

urlpatterns = [
    path('articles/', blog_list, name='blog_list'),                         # ✅ First: specific path
    path('category/<str:category>/', blog_category, name='blog_category'),  # Then category
    path('<slug:slug>/', blog_detail, name='blog_detail'),                 # Last: slug catch-all
]

