import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import Point

from reroute_business.job_list.models import ZipCentroid
from .models import Module, QuizQuestion, QuizAnswer, ModuleQuizScore, ResourceOrganization, Feature


class ModuleQuizTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="quizuser",
            email="quiz@example.com",
            password="safe-password-123",
        )
        self.module = Module.objects.create(
            title="Test Module",
            description="Testing module quiz flow",
            category=Module.CATEGORY_WORKFORCE,
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            key_takeaways=["Always be prepared."],
        )
        self.question = QuizQuestion.objects.create(
            module=self.module,
            prompt="What color is the sky?",
            order=1,
        )
        self.answer_correct = QuizAnswer.objects.create(
            question=self.question,
            text="Blue",
            is_correct=True,
        )
        self.answer_wrong = QuizAnswer.objects.create(
            question=self.question,
            text="Red",
            is_correct=False,
        )

    def test_quiz_schema_returns_questions(self):
        url = reverse("module_quiz_schema", args=[self.module.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module_id"], self.module.id)
        self.assertEqual(len(payload["questions"]), 1)
        question = payload["questions"][0]
        self.assertEqual(question["prompt"], self.question.prompt)
        self.assertEqual(len(question["choices"]), 2)

    def test_quiz_submit_requires_authentication(self):
        url = reverse("module_quiz_submit", args=[self.module.id])
        response = self.client.post(
            url,
            data=json.dumps({
                "answers": [{"question_id": self.question.id, "answer_id": self.answer_correct.id}],
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

    def test_quiz_submit_saves_score(self):
        self.client.login(username="quizuser", password="safe-password-123")
        url = reverse("module_quiz_submit", args=[self.module.id])
        response = self.client.post(
            url,
            data=json.dumps({
                "answers": [{"question_id": self.question.id, "answer_id": self.answer_correct.id}],
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["score"], 1)
        score = ModuleQuizScore.objects.get(module=self.module, user=self.user)
        self.assertEqual(score.score, 1)
        self.assertEqual(score.total_questions, 1)

    def test_inline_quiz_schema_fallback(self):
        self.module.questions.all().delete()
        self.module.quiz_data = {
            "questions": [
                {
                    "id": "intro",
                    "prompt": "Pick A",
                    "choices": [
                        {"id": "a", "text": "A", "is_correct": True},
                        {"id": "b", "text": "B", "is_correct": False},
                    ],
                }
            ]
        }
        self.module.save()

        url = reverse("module_quiz_schema", args=[self.module.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["questions"]), 1)
        self.assertEqual(payload["questions"][0]["choices"][0]["id"], "a")

    def test_inline_quiz_submit_fallback(self):
        self.client.login(username="quizuser", password="safe-password-123")
        self.module.questions.all().delete()
        self.module.quiz_data = {
            "questions": [
                {
                    "id": "intro",
                    "prompt": "Pick A",
                    "choices": [
                        {"id": "a", "text": "A", "is_correct": True},
                        {"id": "b", "text": "B", "is_correct": False},
                    ],
                }
            ]
        }
        self.module.save()

        url = reverse("module_quiz_submit", args=[self.module.id])
        response = self.client.post(
            url,
            data=json.dumps({
                "answers": [{"question_id": "intro", "answer_id": "a"}],
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["score"], 1)


class ResourceDirectoryZipMatchingTests(TestCase):
    def setUp(self):
        self.directory_url = reverse("resource_directory")
        ZipCentroid.objects.create(zip_code="19104", geo_point=Point(-75.1900, 39.9600, srid=4326))
        ZipCentroid.objects.create(zip_code="19147", geo_point=Point(-75.1540, 39.9330, srid=4326))

    def _create_resource(self, name, zip_code):
        return ResourceOrganization.objects.create(
            name=name,
            category=ResourceOrganization.CATEGORY_BENEFITS,
            address_line="123 Main St",
            neighborhood="Philadelphia",
            zip_code=zip_code,
            hours="Mon-Fri",
            phone="5551234567",
            overview="Support services",
            what_to_expect="Expect intake",
            who_can_use_this="Adults",
            how_to_apply="Walk in",
            is_active=True,
        )

    def test_directory_orders_by_distance_when_zip_is_provided(self):
        near = self._create_resource("Near Resource", "19104")
        far = self._create_resource("Far Resource", "19147")
        near.refresh_from_db()
        far.refresh_from_db()
        self.assertIsNotNone(near.geo_point)
        self.assertIsNotNone(far.geo_point)

        response = self.client.get(self.directory_url, {"zip": "19104"})
        self.assertEqual(response.status_code, 200)
        resources = response.context["resources"]
        names = [item["name"] for item in resources]
        self.assertEqual(names[0], "Near Resource")
        self.assertIn("distance_miles", resources[0])

    def test_zip_sorting_stacks_with_feature_filters(self):
        reentry_feature = Feature.objects.create(slug="reentry", label="Reentry")
        near = self._create_resource("Near Filtered Resource", "19104")
        far = self._create_resource("Far Filtered Resource", "19147")
        near.features.add(reentry_feature)
        far.features.add(reentry_feature)

        response = self.client.get(self.directory_url, {"zip": "19104", "features": ["reentry"]})
        self.assertEqual(response.status_code, 200)
        resources = response.context["resources"]
        names = [item["name"] for item in resources]
        self.assertEqual(names[0], "Near Filtered Resource")
        self.assertIn("selected_zip_area", response.context)
        self.assertEqual(response.context["selected_zip_area"], "West Philly / University City")
