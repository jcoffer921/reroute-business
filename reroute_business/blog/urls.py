from django.urls import path

from .views import (
    blog_category,
    blog_detail,
    blog_list,
    journal_create,
    journal_delete,
    journal_detail,
    journal_edit,
    journal_home,
    stories_detail,
    stories_list,
)

urlpatterns = [
    path("", journal_home, name="journal_home"),
    path("new/", journal_create, name="journal_create"),
    path("<int:pk>/", journal_detail, name="journal_detail"),
    path("<int:pk>/edit/", journal_edit, name="journal_edit"),
    path("<int:pk>/delete/", journal_delete, name="journal_delete"),
    path("stories/", stories_list, name="stories_list"),
    path("stories/<slug:slug>/", stories_detail, name="stories_detail"),
    # Legacy compatibility routes
    path("articles/", blog_list, name="blog_list"),
    path("category/<str:category>/", blog_category, name="blog_category"),
    path("<slug:slug>/", blog_detail, name="blog_detail"),
]
