from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q

from .models import ReentryOrganization


def organization_catalog(request):
    q = (request.GET.get('q') or '').strip()
    category = (request.GET.get('category') or '').strip()

    queryset = ReentryOrganization.objects.filter(is_verified=True)
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if category:
        queryset = queryset.filter(category=category)

    page = request.GET.get('page', 1)
    paginator = Paginator(queryset, 12)
    orgs = paginator.get_page(page)

    context = {
        'orgs': orgs,
        'q': q,
        'active_category': category,
        'categories': ReentryOrganization.CATEGORIES,
    }
    return render(request, 'reentry_org/catalog.html', context)
