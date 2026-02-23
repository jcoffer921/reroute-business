from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse

from reroute_business.job_list.models import ZipCentroid
from reroute_business.reentry_org.models import ReentryOrganization


class ReentryCatalogZipMatchingTests(TestCase):
    def setUp(self):
        self.catalog_url = reverse("reentry_org:organization_catalog")
        ZipCentroid.objects.create(zip_code="19104", geo_point=Point(-75.1900, 39.9600, srid=4326))
        ZipCentroid.objects.create(zip_code="19147", geo_point=Point(-75.1540, 39.9330, srid=4326))

    def _create_org(self, name, zip_code):
        return ReentryOrganization.objects.create(
            name=name,
            category="housing",
            description="Housing assistance",
            zip_code=zip_code,
            is_verified=True,
        )

    def test_catalog_orders_closest_organization_first_for_zip(self):
        near = self._create_org("Near Org", "19104")
        far = self._create_org("Far Org", "19147")
        near.refresh_from_db()
        far.refresh_from_db()
        self.assertIsNotNone(near.geo_point)
        self.assertIsNotNone(far.geo_point)

        response = self.client.get(self.catalog_url, {"zip": "19104"})
        self.assertEqual(response.status_code, 200)
        orgs = list(response.context["orgs"].object_list)
        self.assertEqual(orgs[0].name, "Near Org")
