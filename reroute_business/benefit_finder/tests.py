import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class BenefitFinderCompletionTests(TestCase):
    def setUp(self):
        self.complete_url = reverse("benefit_finder:complete")
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="benefit_user",
            email="benefit@example.com",
            password="pass1234",
        )

    def test_complete_endpoint_requires_authentication(self):
        response = self.client.post(
            self.complete_url,
            data=json.dumps({"from_results": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_complete_endpoint_sets_session_flags(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.complete_url,
            data=json.dumps({"from_results": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True, "completed": True})

        session = self.client.session
        self.assertTrue(session.get("benefit_finder_completed"))
        self.assertTrue(session.get("benefit_finder_completed_at"))
        self.assertEqual(session.get("benefit_finder_last_source"), "results")

    def test_complete_endpoint_without_results_payload_still_marks_complete(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.complete_url,
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertTrue(session.get("benefit_finder_completed"))
        self.assertTrue(session.get("benefit_finder_completed_at"))
        self.assertIsNone(session.get("benefit_finder_last_source"))
