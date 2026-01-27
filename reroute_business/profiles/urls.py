# profiles/urls.py
from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    # Owner's profile
    path("", views.user_profile_view, name="my_profile"),

    # Public profile (employer view)
    path("view/<str:username>/", views.public_profile_view, name="public_profile"),

    # Employer profile (owner edit view)
    path("employer/profile/", views.employer_profile_view, name="employer_profile"),
    # Public employer profile (read-only, by username)
    path("employer/view/<str:username>/", views.employer_public_profile_view, name="employer_public_profile"),
    path("employer/logo/remove/", views.remove_employer_logo, name="remove_employer_logo"),

    # Subscription settings
    path("settings/subscription/", views.subscription_settings, name="subscription_settings"),
    path("settings/subscription/cancel/", views.cancel_subscription, name="cancel_subscription"),
]
