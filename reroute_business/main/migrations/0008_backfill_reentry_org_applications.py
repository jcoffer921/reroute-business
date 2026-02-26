from django.db import migrations


def forward(apps, schema_editor):
    AgencyPartnershipApplication = apps.get_model("main", "AgencyPartnershipApplication")
    ReentryOrgApplication = apps.get_model("reentry_org", "ReentryOrgApplication")

    status_map = {
        "submitted": "pending",
        "in_review": "pending",
        "approved": "approved",
        "rejected": "rejected",
    }
    referral_map = {
        "website_link": "website",
        "email_referral": "email",
        "phone_referral": "phone",
        "api_future": "api_future",
    }

    legacy_rows = AgencyPartnershipApplication.objects.exclude(status="draft").order_by("id")
    for legacy in legacy_rows.iterator():
        org_name = (legacy.organization_name or "").strip()
        contact_email = (legacy.contact_email or "").strip()
        if not org_name and not contact_email:
            continue

        qs = ReentryOrgApplication.objects.filter(org_name=org_name, contact_email=contact_email)
        if legacy.submitted_at:
            qs = qs.filter(submitted_at__date=legacy.submitted_at.date())
        if qs.exists():
            continue

        created = ReentryOrgApplication.objects.create(
            org_name=org_name,
            primary_contact_name=legacy.primary_contact_name or "",
            contact_email=contact_email,
            contact_phone=legacy.contact_phone or "",
            website=legacy.website or "",
            physical_address=legacy.physical_address or "",
            service_area=legacy.service_area or "",
            year_founded=legacy.year_founded,
            organization_type=legacy.organization_type or "",
            services=legacy.services_offered or [],
            other_services=legacy.services_other or "",
            serve_justice_impacted=bool(legacy.supports_justice_impacted),
            serve_recently_released=bool(legacy.supports_recently_released),
            additional_populations=legacy.target_population or [],
            other_populations=legacy.target_population_other or "",
            program_criteria=legacy.additional_eligibility_details or "",
            requires_id=bool(legacy.requires_government_id),
            requires_orientation=bool(legacy.requires_orientation_attendance),
            requires_intake_assessment=bool(legacy.requires_intake_assessment),
            requires_residency_in_service_area=bool(legacy.requires_service_area_residency),
            avg_served_per_month=legacy.average_served_per_month,
            intake_process_description=legacy.intake_process_description or "",
            preferred_referral_method=referral_map.get(legacy.referral_method_preference, "api_future"),
            tracks_employment_outcomes=legacy.tracks_employment_outcomes,
            open_to_referral_tracking=legacy.open_to_referral_tracking,
            why_partner=legacy.partnership_reason or "",
            how_reroute_can_support=legacy.reroute_support_needs or "",
            interested_featured_verified=legacy.interested_in_featured_verified,
            accuracy_confirmation=bool(legacy.accuracy_confirmation),
            terms_privacy_agreement=bool(legacy.terms_privacy_agreement),
            status=status_map.get(legacy.status, "pending"),
            reviewed_at=legacy.reviewed_at,
            reviewed_by_id=legacy.reviewed_by_id,
        )
        if legacy.logo:
            created.logo = legacy.logo
            created.save(update_fields=["logo"])

        if legacy.submitted_at:
            ReentryOrgApplication.objects.filter(pk=created.pk).update(submitted_at=legacy.submitted_at)


def backward(apps, schema_editor):
    # No-op: do not delete migrated application records.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_youtubevideo_duration_and_quiz_lesson_count"),
        ("reentry_org", "0008_reentryorgapplication_resource_organization"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
