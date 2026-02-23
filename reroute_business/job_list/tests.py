import os
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import TestCase
from io import StringIO
from tempfile import NamedTemporaryFile

from reroute_business.job_list.models import Job, ZipCentroid
from reroute_business.job_list.services.matching import get_nearby_jobs
from reroute_business.job_list.utils.location import zip_to_point


class NearbyJobMatchingTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(username="employer_geo", password="x")
        self.seeker = User.objects.create_user(username="seeker_geo", password="x")
        self.profile = self.seeker.profile

        # Philadelphia centroid sample
        self.center = Point(-75.1652, 39.9526, srid=4326)
        ZipCentroid.objects.create(zip_code="19104", geo_point=self.center)

    def _create_job(self, title, point=None, **extra):
        payload = {
            "title": title,
            "description": "desc",
            "requirements": "req",
            "location": "Philadelphia, PA",
            "zip_code": "19104",
            "employer": self.employer,
            "tags": "general",
            "geo_point": point,
        }
        payload.update(extra)
        return Job.objects.create(**payload)

    def test_users_without_geo_point_get_no_nearby_results(self):
        self.profile.geo_point = None
        self.profile.zip_code = ""
        self.profile.save(update_fields=["geo_point", "zip_code"])

        self._create_job("Nearby", point=Point(-75.1600, 39.9500, srid=4326))
        qs = get_nearby_jobs(self.profile, miles=25)
        self.assertEqual(qs.count(), 0)

    def test_valid_zip_assigns_profile_geo_and_filters_radius(self):
        self.profile.zip_code = "19104"
        self.profile.geo_point = None
        self.profile.save()
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.geo_point)

        near_job = self._create_job("Near Job", point=Point(-75.1600, 39.9500, srid=4326))
        far_job = self._create_job("Far Job", point=Point(-74.0000, 40.7000, srid=4326), zip_code="10001")

        result_ids = list(get_nearby_jobs(self.profile, miles=25).values_list("id", flat=True))
        self.assertIn(near_job.id, result_ids)
        self.assertNotIn(far_job.id, result_ids)

    def test_job_geo_point_auto_populates_from_zip(self):
        job = self._create_job("Signal ZIP Job", point=None, zip_code="19104")
        self.assertIsNotNone(job.geo_point)

    def test_distance_annotation_is_present(self):
        self.profile.zip_code = "19104"
        self.profile.geo_point = None
        self.profile.save()

        self._create_job("Near Job", point=Point(-75.1600, 39.9500, srid=4326))
        first = get_nearby_jobs(self.profile, miles=25).first()
        self.assertIsNotNone(first)
        self.assertTrue(hasattr(first, "distance"))

    def test_remote_jobs_included_even_if_outside_radius(self):
        self.profile.zip_code = "19104"
        self.profile.geo_point = None
        self.profile.save()

        near_job = self._create_job("Near Job", point=Point(-75.1600, 39.9500, srid=4326))
        far_remote = self._create_job(
            "Far Remote Job",
            point=Point(-118.2437, 34.0522, srid=4326),
            zip_code="90001",
            is_remote=True,
        )
        far_onsite = self._create_job(
            "Far Onsite Job",
            point=Point(-118.2437, 34.0522, srid=4326),
            zip_code="90001",
            is_remote=False,
        )

        result_ids = list(get_nearby_jobs(self.profile, miles=10).values_list("id", flat=True))
        self.assertIn(near_job.id, result_ids)
        self.assertIn(far_remote.id, result_ids)
        self.assertNotIn(far_onsite.id, result_ids)

    def test_remote_jobs_not_returned_when_user_has_no_geo_point(self):
        self.profile.geo_point = None
        self.profile.zip_code = ""
        self.profile.save(update_fields=["geo_point", "zip_code"])

        remote_job = self._create_job(
            "Remote Job",
            point=None,
            zip_code="",
            is_remote=True,
        )
        self.assertTrue(Job.objects.filter(pk=remote_job.pk).exists())
        result_ids = list(get_nearby_jobs(self.profile, miles=25).values_list("id", flat=True))
        self.assertEqual(result_ids, [])

    def test_zip_to_point_lookup(self):
        point = zip_to_point("19104")
        self.assertIsNotNone(point)

    def test_spatial_index_is_declared(self):
        self.assertTrue(any("geo_point" in idx.fields for idx in Job._meta.indexes))
        self.assertTrue(any("geo_point" in idx.fields for idx in ZipCentroid._meta.indexes))

    def test_import_zip_centroids_command_creates_points(self):
        tmp = NamedTemporaryFile("w", suffix=".csv", encoding="utf-8", delete=False)
        try:
            tmp.write("zip_code,latitude,longitude\n")
            tmp.write("19139,39.9610,-75.2320\n")
            tmp.write("19140,39.9950,-75.1460\n")
            tmp.write("badzip,notalat,-75.1000\n")
            tmp.close()
            stdout = StringIO()
            call_command("import_zip_centroids", tmp.name, stdout=stdout)
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

        self.assertTrue(ZipCentroid.objects.filter(zip_code="19139").exists())
        self.assertTrue(ZipCentroid.objects.filter(zip_code="19140").exists())
        self.assertIn("Inserted:", stdout.getvalue())
        self.assertIn("Skipped:", stdout.getvalue())
