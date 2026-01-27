from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# project urls.py (add these imports)
from reroute_business.main import views as main_views                   # for dashboard view
from reroute_business.profiles.views import (
    user_profile_view,            # owner profile (redirects to settings)
    employer_profile_view,        # employer profile alias
    employer_public_profile_view,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reroute_business.main.urls')),

    # Aliases (exact paths for convenience) --> NEEDED
    path('profile/', user_profile_view, name='my_profile'),  # exact-path alias
    # Ensure a global name for employer profile to support `{% url 'employer_profile' %}` in templates
    path('profile/employer/profile/', employer_profile_view, name='employer_profile'),
    path('profile/employer/view/<str:username>/', employer_public_profile_view, name='employer_public_profile'),
    # --- EXACT-PATH ALIASES (these create the names your templates use) ---
    path('profile/',   user_profile_view,         name='my_profile'),  # /profile/ resolves by name
    path('dashboard/', main_views.dashboard_view, name='dashboard'),   # /dashboard/ resolves by name

    # --- APP INCLUDES (handle deeper paths under same prefixes) ---
    # Include profiles with namespace so templates can use `profiles:...`
    path('profile/',   include(('reroute_business.profiles.urls', 'profiles'), namespace='profiles')),  # /profile/update/... /profile/view/<username>/
    path('dashboard/', include(('reroute_business.dashboard.urls', 'dashboard'), namespace='dashboard')),

    # (the rest you already have)
    path('jobs/',      include('reroute_business.job_list.urls')),
    path('resume/',    include(('reroute_business.resumes.urls', 'resumes'), namespace='resumes')),
    path('accounts/',  include('allauth.urls')),
    path('resources/', include('reroute_business.resources.urls')),
    path('organizations/', include(('reroute_business.reentry_org.urls', 'reentry_org'), namespace='reentry_org')),
    path('blog/',      include('reroute_business.blog.urls')),
    path('api/',       include('reroute_business.core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
