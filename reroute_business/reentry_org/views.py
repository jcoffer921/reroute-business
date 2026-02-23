from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.utils import ProgrammingError, OperationalError
from django.db.models import F, Q
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from reroute_business.job_list.utils.location import zip_to_point
from .models import ReentryOrganization, SavedOrganization

if settings.USE_GIS:
    from django.contrib.gis.db.models.functions import Distance


def organization_catalog(request):
    q = (request.GET.get('q') or '').strip()
    category = (request.GET.get('category') or '').strip()
    zip_code = (request.GET.get('zip') or '').strip()
    if not zip_code.isdigit() or len(zip_code) != 5:
        zip_code = ''

    queryset = ReentryOrganization.objects.filter(is_verified=True)
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if category:
        queryset = queryset.filter(category=category)
    user_point = zip_to_point(zip_code) if (settings.USE_GIS and zip_code) else None
    if settings.USE_GIS and user_point:
        queryset = queryset.annotate(distance=Distance("geo_point", user_point)).order_by(
            F("distance").asc(nulls_last=True),
            "name",
        )
    else:
        queryset = queryset.order_by("name")

    page = request.GET.get('page', 1)
    try:
        paginator = Paginator(queryset, 12)
        orgs = paginator.get_page(page)
    except (ProgrammingError, OperationalError):
        paginator = Paginator(ReentryOrganization.objects.none(), 12)
        orgs = paginator.get_page(1)

    context = {
        'orgs': orgs,
        'q': q,
        'active_category': category,
        'selected_zip': zip_code,
        'categories': ReentryOrganization.CATEGORIES,
    }
    return render(request, 'reentry_org/catalog.html', context)


@login_required
@require_POST
def toggle_saved_org(request):
    org_id = request.POST.get("organization_id")
    redirect_to = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse('dashboard:user')

    if not org_id:
        return redirect(redirect_to)

    org = get_object_or_404(ReentryOrganization, pk=org_id)

    existing = SavedOrganization.objects.filter(user=request.user, organization=org)
    if existing.exists():
        existing.delete()
    else:
        SavedOrganization.objects.create(user=request.user, organization=org)

    return redirect(redirect_to)
