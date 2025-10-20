from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# project urls.py (add these imports)
from reroute_business.main import views as main_views                   # for dashboard view
from reroute_business.profiles.views import (
    update_demographics,
    update_emergency_contact,
    update_employment_info,
    update_personal_info,
    update_skills,
    user_profile_view,            # owner profile
    update_profile_picture,
    remove_profile_picture,
    update_bio,
    employer_profile_view,        # employer profile alias
    employer_public_profile_view,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reroute_businessmain.urls')),

    # Aliases (exact paths for convenience) --> NEEDED
    path('profile/', user_profile_view, name='my_profile'),  # exact-path alias
    # Ensure a global name for employer profile to support `{% url 'employer_profile' %}` in templates
    path('profile/employer/profile/', employer_profile_view, name='employer_profile'),
    path('profile/employer/view/<str:username>/', employer_public_profile_view, name='employer_public_profile'),
    path('profile/update-picture/', update_profile_picture, name='update_profile_picture'),
    path('profile/remove-picture/', remove_profile_picture, name='remove_profile_picture'),
    path('profile/update-bio/', update_bio, name='update_bio'), 
    path('profile/update/personal/',     update_personal_info,    name='update_personal_info'),
    path('profile/update/employment/',   update_employment_info,  name='update_employment_info'),
    path('profile/update/emergency/',    update_emergency_contact,name='update_emergency_contact'),
    path('profile/update/demographics/', update_demographics,     name='update_demographics'),
    path('profile/update/skills/',       update_skills,           name='update_skills'),

    # --- EXACT-PATH ALIASES (these create the names your templates use) ---
    path('profile/',   user_profile_view,         name='my_profile'),  # /profile/ resolves by name
    path('dashboard/', main_views.dashboard_view, name='dashboard'),   # /dashboard/ resolves by name

    # --- APP INCLUDES (handle deeper paths under same prefixes) ---
    # Include profiles with namespace so templates can use `profiles:...`
    path('profile/',   include(('profiles.urls', 'profiles'), namespace='profiles')),  # /profile/update/... /profile/view/<username>/
    path('dashboard/', include(('dashboard.urls', 'dashboard'), namespace='dashboard')),

    # (the rest you already have)
    path('jobs/',      include('job_list.urls')),
    path('resume/',    include(('resumes.urls', 'resumes'), namespace='resumes')),
    path('accounts/',  include('allauth.urls')),
    path('resources/', include('resources.urls')),
    path('organizations/', include('reentry_org.urls')),
    path('blog/',      include('blog.urls')),
    path('api/',       include('core.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
