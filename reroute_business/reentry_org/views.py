from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.utils import ProgrammingError, OperationalError
from django.db.models import F, Q
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required

from reroute_business.job_list.utils.location import zip_to_point
from .models import ReentryOrganization, SavedOrganization, ReentryOrgApplication

if settings.USE_GIS:
    from django.contrib.gis.db.models.functions import Distance


def organization_catalog(request):
    q = (request.GET.get('q') or '').strip()
    category = (request.GET.get('category') or '').strip()
    zip_code = (request.GET.get('zip') or '').strip()
    saved_only = (request.GET.get('saved') or '').strip().lower() in {"1", "true", "yes", "on"}
    if not zip_code.isdigit() or len(zip_code) != 5:
        zip_code = ''

    queryset = ReentryOrganization.objects.all()
    if saved_only:
        if request.user.is_authenticated:
            queryset = queryset.filter(saves__user=request.user).distinct()
        else:
            queryset = queryset.none()
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if category:
        queryset = queryset.filter(category=category)
    user_point = zip_to_point(zip_code) if (settings.USE_GIS and zip_code) else None
    if settings.USE_GIS and user_point:
        queryset = queryset.annotate(distance=Distance("geo_point", user_point)).order_by(
            F("is_verified").desc(),
            F("distance").asc(nulls_last=True),
            "name",
        )
    else:
        queryset = queryset.order_by("-is_verified", "name")

    page = request.GET.get('page', 1)
    try:
        paginator = Paginator(queryset, 10)
        orgs = paginator.get_page(page)
    except (ProgrammingError, OperationalError):
        paginator = Paginator(ReentryOrganization.objects.none(), 10)
        orgs = paginator.get_page(1)

    context = {
        'orgs': orgs,
        'q': q,
        'active_category': category,
        'selected_zip': zip_code,
        'saved_only': saved_only,
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


@staff_member_required
def application_pdf(request, application_id):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.utils import simpleSplit
        from reportlab.pdfgen import canvas
    except ModuleNotFoundError:
        return HttpResponse(
            "ReportLab is not installed in this environment.",
            status=500,
            content_type="text/plain",
        )

    application = get_object_or_404(ReentryOrgApplication, pk=application_id)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="reentry_org_application_{application.pk}.pdf"'

    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    margin = 54
    y = height - margin
    body_font = "Helvetica"
    body_size = 10.5
    line_height = 14

    def ensure_space(required=40):
        nonlocal y
        if y < margin + required:
            pdf.showPage()
            y = height - margin
            pdf.setFont(body_font, body_size)

    def draw_header(text):
        nonlocal y
        ensure_space(36)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(margin, y, text)
        y -= 24
        pdf.setFont(body_font, body_size)

    def draw_section(title):
        nonlocal y
        ensure_space(30)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(margin, y, title)
        y -= 18
        pdf.setFont(body_font, body_size)

    def draw_kv(label, value):
        nonlocal y
        value_text = "Yes" if value is True else "No" if value is False else (str(value).strip() if value not in (None, "") else "—")
        wrapped = simpleSplit(f"{label}: {value_text}", body_font, body_size, width - (margin * 2))
        ensure_space((len(wrapped) * line_height) + 6)
        for line in wrapped:
            pdf.drawString(margin, y, line)
            y -= line_height
        y -= 2

    def csv_or_dash(values):
        if not values:
            return "—"
        if isinstance(values, (list, tuple)):
            return ", ".join(str(v) for v in values)
        return str(values)

    draw_header("ReRoute - Reentry Organization Application")

    draw_section("Step 1: Organization Information")
    draw_kv("Organization Name", application.org_name)
    draw_kv("Primary Contact Name", application.primary_contact_name)
    draw_kv("Contact Email", application.contact_email)
    draw_kv("Contact Phone", application.contact_phone)
    draw_kv("Website", application.website)
    draw_kv("Physical Address", application.physical_address)
    draw_kv("Service Area", application.service_area)
    draw_kv("Year Founded", application.year_founded)
    draw_kv("Organization Type", application.get_organization_type_display() if application.organization_type else "—")

    draw_section("Step 2: Services")
    draw_kv("Services", csv_or_dash(application.services))
    draw_kv("Other Services", application.other_services)

    draw_section("Step 3: Population + Program Criteria")
    draw_kv("Serve justice-impacted individuals", application.serve_justice_impacted)
    draw_kv("Serve recently released individuals", application.serve_recently_released)
    draw_kv("Additional Populations", csv_or_dash(application.additional_populations))
    draw_kv("Other Populations", application.other_populations)
    draw_kv("Program Criteria", application.program_criteria)
    draw_kv("Requires ID", application.requires_id)
    draw_kv("Requires Orientation", application.requires_orientation)
    draw_kv("Requires Intake Assessment", application.requires_intake_assessment)
    draw_kv("Requires Residency in Service Area", application.requires_residency_in_service_area)

    draw_section("Step 4: Capacity & Operations")
    draw_kv("Average Served Per Month", application.avg_served_per_month)
    draw_kv("Intake Process Description", application.intake_process_description)
    draw_kv(
        "Preferred Referral Method",
        application.get_preferred_referral_method_display() if application.preferred_referral_method else "—",
    )
    draw_kv("Tracks Employment Outcomes", application.tracks_employment_outcomes)
    draw_kv("Open to Referral Tracking", application.open_to_referral_tracking)

    draw_section("Step 5: Partnership Alignment")
    draw_kv("Why Partner", application.why_partner)
    draw_kv("How ReRoute Can Support", application.how_reroute_can_support)
    draw_kv("Interested Featured Verified", application.interested_featured_verified)

    draw_section("Step 6: Compliance & Consent")
    draw_kv("Accuracy Confirmation", application.accuracy_confirmation)
    draw_kv("Terms Privacy Agreement", application.terms_privacy_agreement)
    draw_kv("Logo Uploaded", "Yes" if application.logo else "No")

    draw_section("Review Metadata")
    draw_kv("Status", application.get_status_display())
    draw_kv("Submitted At", application.submitted_at)
    draw_kv("Reviewed At", application.reviewed_at)
    draw_kv("Reviewed By", application.reviewed_by)

    pdf.showPage()
    pdf.save()
    return response
