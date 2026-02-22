from django.db import migrations, models


def seed_resource_organizations(apps, schema_editor):
    ResourceOrganization = apps.get_model("resources", "ResourceOrganization")

    records = [
        {
            "slug": "penndot-id-center",
            "name": "PennDOT ID Center",
            "categories": ["ID/Documents"],
            "features": ["Near Public Transit", "No Appointment Needed"],
            "address_line": "801 Arch St, Philadelphia, PA 19107",
            "neighborhood": "Old City",
            "transit_line": "Near 8th & Market (MFL)",
            "zip_code": "19107",
            "hours": "Mon–Fri 8:30am–4:15pm",
            "phone": "(717) 412-5300",
            "phone_href": "+17174125300",
            "website": "https://www.dmv.pa.gov/Driver-Services/Photo-ID2/Pages/Get%20An%20ID.aspx",
            "overview": "Get a Pennsylvania state ID card or driver's license. Discounted IDs available for recently released individuals.",
            "what_to_expect": "Take a number when you arrive. Wait times can be long—arrive early. Staff will guide you through the process.",
            "who_can_use_this": "Open to all Pennsylvania residents. Reduced fee for people released from prison within 1 year.",
            "what_to_bring": [
                "Social Security card",
                "Birth certificate or passport",
                "Two proofs of residency",
                "Release papers (for discounted ID)",
            ],
            "how_to_apply": "Walk in during business hours. Bring all required documents.",
            "getting_there": "Take MFL to 8th Street, walk 1 block north.",
            "languages_supported": ["English"],
            "cultural_competency": [],
            "childcare_support": "",
            "is_active": True,
        },
        {
            "slug": "congreso-de-latinos-unidos",
            "name": "Congreso de Latinos Unidos",
            "categories": ["Job Training"],
            "features": [
                "Spanish Available",
                "Bilingual Staff",
                "Culturally Specific",
                "Trauma-Informed",
                "Near Public Transit",
                "Childcare Support",
            ],
            "address_line": "216 W Somerset St, Philadelphia, PA 19133",
            "neighborhood": "Fairhill / North Philadelphia",
            "transit_line": "Near SEPTA Bus Routes 3, 39, 54",
            "zip_code": "19133",
            "hours": "Mon–Fri 8:30am–5pm",
            "phone": "(215) 763-8870",
            "phone_href": "+12157638870",
            "website": "https://www.congreso.net/",
            "overview": "Bilingual workforce development and social services for Philadelphia's Latino community. Offers job training, ESL, GED, and family services.",
            "what_to_expect": "All services available in Spanish and English. Very welcoming environment. Staff understands the challenges faced by Latino families.",
            "who_can_use_this": "Open to all. Designed primarily for Latino community but serves everyone.",
            "what_to_bring": [
                "Photo ID (if available)",
                "Any work or education documents",
            ],
            "how_to_apply": "Call or walk in during office hours.",
            "getting_there": "SEPTA Bus 39 stops at Somerset & 2nd St.",
            "languages_supported": ["English", "Spanish"],
            "cultural_competency": ["Trauma-Informed", "Culturally Specific"],
            "childcare_support": "Childcare available on-site during some programs. Call ahead to confirm.",
            "is_active": True,
        },
    ]

    for record in records:
        ResourceOrganization.objects.update_or_create(slug=record["slug"], defaults=record)


def unseed_resource_organizations(apps, schema_editor):
    ResourceOrganization = apps.get_model("resources", "ResourceOrganization")
    ResourceOrganization.objects.filter(
        slug__in=["penndot-id-center", "congreso-de-latinos-unidos"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0009_module_is_archived"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResourceOrganization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=200, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("categories", models.JSONField(blank=True, default=list)),
                ("features", models.JSONField(blank=True, default=list)),
                ("address_line", models.CharField(max_length=255)),
                ("neighborhood", models.CharField(blank=True, max_length=255)),
                ("transit_line", models.CharField(blank=True, max_length=255)),
                ("zip_code", models.CharField(blank=True, max_length=5)),
                ("hours", models.CharField(blank=True, max_length=255)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("phone_href", models.CharField(blank=True, max_length=50)),
                ("website", models.URLField(blank=True)),
                ("overview", models.TextField(blank=True)),
                ("what_to_expect", models.TextField(blank=True)),
                ("who_can_use_this", models.TextField(blank=True)),
                ("what_to_bring", models.JSONField(blank=True, default=list)),
                ("how_to_apply", models.TextField(blank=True)),
                ("getting_there", models.TextField(blank=True)),
                ("languages_supported", models.JSONField(blank=True, default=list)),
                ("cultural_competency", models.JSONField(blank=True, default=list)),
                ("childcare_support", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Resource Organization",
                "verbose_name_plural": "Resource Organizations",
                "ordering": ("name",),
            },
        ),
        migrations.RunPython(seed_resource_organizations, unseed_resource_organizations),
    ]
