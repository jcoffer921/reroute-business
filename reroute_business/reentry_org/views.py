from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.utils import ProgrammingError, OperationalError
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .models import ReentryOrganization, SavedOrganization


def organization_catalog(request):
    q = (request.GET.get('q') or '').strip()
    category = (request.GET.get('category') or '').strip()

    queryset = ReentryOrganization.objects.filter(is_verified=True)
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if category:
        queryset = queryset.filter(category=category)

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
