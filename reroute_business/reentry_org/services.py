from __future__ import annotations

from typing import Iterable

from reroute_business.resources.models import ResourceOrganization

from .models import ReentryOrgApplication


def _extract_zip(*values: str) -> str:
    for value in values:
        raw = "".join(ch for ch in str(value or "") if ch.isdigit())
        if len(raw) >= 5:
            return raw[:5]
    return ""


def _clean_services(services: Iterable[str]) -> list[str]:
    cleaned = []
    for value in services or []:
        text = str(value).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _map_category(application: ReentryOrgApplication) -> str:
    service_text = " ".join(_clean_services(application.services)).lower()
    haystack = " ".join(
        [
            service_text,
            str(application.other_services or "").lower(),
            str(application.program_criteria or "").lower(),
        ]
    )

    mapping = [
        (("housing", "shelter"), ResourceOrganization.CATEGORY_HOUSING),
        (("food", "meal", "pantry"), ResourceOrganization.CATEGORY_FOOD),
        (("id", "document", "birth certificate", "license"), ResourceOrganization.CATEGORY_ID_DOCUMENTS),
        (("benefit", "snap", "tanf", "ssi", "ssdi", "medicaid"), ResourceOrganization.CATEGORY_BENEFITS),
        (("mental", "counsel", "therapy"), ResourceOrganization.CATEGORY_MENTAL_HEALTH),
        (("substance", "recovery", "addiction"), ResourceOrganization.CATEGORY_SUBSTANCE_USE),
        (("health", "medical", "clinic"), ResourceOrganization.CATEGORY_HEALTHCARE),
        (("legal", "expungement", "court"), ResourceOrganization.CATEGORY_LEGAL),
        (("job", "employment", "interview", "workforce", "career"), ResourceOrganization.CATEGORY_WORKFORCE_DEV),
        (("education", "training", "literacy"), ResourceOrganization.CATEGORY_EDUCATION),
        (("case management", "navigation"), ResourceOrganization.CATEGORY_CASE_MANAGEMENT),
        (("multi", "full service"), ResourceOrganization.CATEGORY_MULTI_SERVICE),
        (("transport",), ResourceOrganization.CATEGORY_REENTRY_ORGS),
    ]

    for keywords, category in mapping:
        if any(keyword in haystack for keyword in keywords):
            return category

    return ResourceOrganization.CATEGORY_REENTRY_ORGS


def upsert_resource_org_from_application(application: ReentryOrgApplication) -> ResourceOrganization:
    """Create or update the canonical ResourceOrganization from an org application."""
    website = (application.website or "").strip()
    org_name = (application.org_name or "").strip()

    existing = None
    if application.resource_organization_id:
        existing = ResourceOrganization.objects.filter(pk=application.resource_organization_id).first()
    if existing is None and website:
        existing = ResourceOrganization.objects.filter(website__iexact=website).first()
    if existing is None and org_name:
        existing = ResourceOrganization.objects.filter(name__iexact=org_name).first()

    if existing is None:
        existing = ResourceOrganization(name=org_name or "Unnamed Organization", address_line="Address not provided")

    zip_code = _extract_zip(application.physical_address, application.service_area)

    existing.name = org_name or existing.name
    existing.category = _map_category(application)
    existing.address_line = (application.physical_address or existing.address_line or "Address not provided").strip() or "Address not provided"
    existing.neighborhood = (application.service_area or "").strip()[:255]
    existing.zip_code = zip_code
    existing.phone = (application.contact_phone or "").strip()
    existing.phone_href = (application.contact_phone or "").strip()
    existing.website = website
    existing.overview = (application.why_partner or application.intake_process_description or application.program_criteria or "").strip()
    existing.who_can_use_this = (application.other_populations or "").strip()
    existing.how_to_apply = (application.intake_process_description or "").strip()
    existing.languages_supported = []
    existing.cultural_competency = []
    existing.is_active = True
    existing.save()

    if application.resource_organization_id != existing.id:
        application.resource_organization = existing
        application.save(update_fields=["resource_organization"])

    return existing
