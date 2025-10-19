# profiles/urls.py
from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    # Owner's profile
    path("", views.user_profile_view, name="my_profile"),

    # Public profile (employer view)
    path("view/<str:username>/", views.public_profile_view, name="public_profile"),

    # Updates (slide-in panels)
    path("update/bio/", views.update_bio, name="update_bio"),
    path("update/personal/", views.update_personal_info, name="update_personal_info"),
    path("update/employment/", views.update_employment_info, name="update_employment_info"),
    path("update/emergency/", views.update_emergency_contact, name="update_emergency_contact"),
    path("update/demographics/", views.update_demographics, name="update_demographics"),
    path("update/skills/", views.update_skills, name="update_skills"),

    # Profile picture
    path("update-picture/", views.update_profile_picture, name="update_profile_picture"),
    path("remove-picture/", views.remove_profile_picture, name="remove_profile_picture"),
    # Background image
    path("update-background/", views.update_profile_background, name="update_profile_background"),
    path("remove-background/", views.remove_profile_background, name="remove_profile_background"),

    # Employer profile (owner edit view)
    path("employer/profile/", views.employer_profile_view, name="employer_profile"),
    # Public employer profile (read-only, by username)
    path("employer/view/<str:username>/", views.employer_public_profile_view, name="employer_public_profile"),
    path("employer/logo/remove/", views.remove_employer_logo, name="remove_employer_logo"),

    # Subscription settings
    path("settings/subscription/", views.subscription_settings, name="subscription_settings"),
    path("settings/subscription/cancel/", views.cancel_subscription, name="cancel_subscription"),
]
