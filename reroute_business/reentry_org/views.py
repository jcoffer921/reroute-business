from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import ReentryOrganization


def organization_catalog(request):
    # Filters
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    city = request.GET.get('city', '').strip()
    state = request.GET.get('state', '').strip()

    queryset = ReentryOrganization.objects.filter(is_verified=True)

    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )
    if category:
        queryset = queryset.filter(category=category)
    if city:
        queryset = queryset.filter(city__iexact=city)
    if state:
        queryset = queryset.filter(state__iexact=state)

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(queryset, 12)  # 12 per page (3x4 on desktop)
    try:
        orgs = paginator.page(page)
    except PageNotAnInteger:
        orgs = paginator.page(1)
    except EmptyPage:
        orgs = paginator.page(paginator.num_pages)

    context = {
        'orgs': orgs,
        'q': q,
        'active_category': category,
        'categories': ReentryOrganization.CATEGORIES,
        'city': city,
        'state': state,
    }
    return render(request, 'reentry_org/catalog.html', context)


def organization_detail(request, pk: int):
    org = get_object_or_404(ReentryOrganization, pk=pk, is_verified=True)
    context = {
        'org': org,
        'categories': ReentryOrganization.CATEGORIES,
    }
    return render(request, 'reentry_org/detail.html', context)


# Create your views here.
