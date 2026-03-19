import json
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.conf import settings

try:
    from django.contrib.gis.geos import Point
except ImproperlyConfigured:
    Point = None

from reroute_business.job_list.models import ZipCentroid
from .models import (
    Module,
    ModuleAttempt,
    ModuleProgress,
    QuizQuestion,
    QuizAnswer,
    ModuleQuizScore,
    ModuleResponse,
    ResourceOrganization,
    Feature,
    Lesson,
    LessonProgress,
)


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
            explanation="Blue is the correct answer because the atmosphere scatters blue light.",
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
        self.assertNotIn("is_correct", question["choices"][0])

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
        self.assertIn(str(self.question.id), payload["evaluation"])
        self.assertEqual(
            payload["evaluation"][str(self.question.id)]["explanation"],
            self.question.explanation,
        )
        score = ModuleQuizScore.objects.get(module=self.module, user=self.user)
        self.assertEqual(score.score, 1)
        self.assertEqual(score.total_questions, 1)
        progress = ModuleProgress.objects.get(module=self.module, user=self.user)
        self.assertIsNotNone(progress.completed_at)
        self.assertEqual(progress.last_question_order, 1)
        attempt = ModuleAttempt.objects.get(module=self.module, user=self.user)
        self.assertEqual(attempt.score, 1)
        response_record = ModuleResponse.objects.get(attempt=attempt)
        self.assertEqual(response_record.selected_answer, self.answer_correct)
        self.assertTrue(response_record.is_correct)

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

    def test_module_progress_endpoint_persists_completion(self):
        self.client.login(username="quizuser", password="safe-password-123")
        url = reverse("module_progress", args=[self.module.id])
        response = self.client.post(
            url,
            data=json.dumps({
                "last_question_order": 1,
                "score_percent": 50,
                "completed": True,
                "raw_state": {"answers": {"1": {"value": str(self.answer_correct.id), "qtype": "mc"}}},
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        progress = ModuleProgress.objects.get(module=self.module, user=self.user)
        self.assertEqual(progress.last_question_order, 1)
        self.assertEqual(progress.score_percent, 50)
        self.assertIsNotNone(progress.completed_at)
        self.assertEqual(response.json()["progress"]["last_question_order"], 1)

    def test_module_detail_recommends_related_modules(self):
        related = Module.objects.create(
            title="Next Module",
            description="Continue learning",
            category=self.module.category,
            gallery_category=self.module.gallery_category,
            video_url="https://www.youtube.com/watch?v=oHg5SJYRHA0",
        )
        response = self.client.get(reverse("module_detail", args=[self.module.id]))
        self.assertEqual(response.status_code, 200)
        related_ids = [item.id for item in response.context["related_modules"]]
        self.assertIn(related.id, related_ids)


class LessonProgressTests(TestCase):
    def setUp(self):
        self.lesson = Lesson.objects.create(
            title="Lesson One",
            slug="lesson-one",
            description="Test lesson",
            video_static_path="/static/resources/videos/test.mp4",
            duration_seconds=120,
        )

    def test_lesson_progress_round_trip_in_schema(self):
        progress_url = reverse("lesson_progress", args=[self.lesson.slug])
        response = self.client.post(
            progress_url,
            data=json.dumps({
                "last_video_time": 42,
                "last_answered_question_order": 3,
                "raw_state": {"answers": {"5": {"open_text": "hello"}}},
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        schema_url = reverse("lesson_schema", args=[self.lesson.slug])
        schema_response = self.client.get(schema_url)
        self.assertEqual(schema_response.status_code, 200)
        progress = schema_response.json()["progress"]
        self.assertEqual(progress["last_video_time"], 42)
        self.assertEqual(progress["last_answered_question_order"], 3)
        self.assertEqual(progress["raw_state"]["answers"]["5"]["open_text"], "hello")
        self.assertEqual(LessonProgress.objects.get(lesson=self.lesson).last_answered_question_order, 3)

    def test_lesson_schema_includes_explanation_field(self):
        question = self.lesson.questions.create(
            order=1,
            timestamp_seconds=12,
            prompt="What should you do first?",
            explanation="Start by identifying the main goal of the task.",
            qtype="OPEN_ENDED",
        )
        response = self.client.get(reverse("lesson_schema", args=[self.lesson.slug]))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["questions"][0]["explanation"], question.explanation)


class LearningValidationTests(TestCase):
    def test_multiple_choice_question_requires_one_correct_answer(self):
        module = Module.objects.create(
            title="Validation Module",
            category=Module.CATEGORY_WORKFORCE,
        )
        question = QuizQuestion.objects.create(
            module=module,
            prompt="Choose one",
            qtype=QuizQuestion.QTYPE_MULTIPLE_CHOICE,
        )
        QuizAnswer.objects.create(question=question, text="A", is_correct=False)
        with self.assertRaises(ValidationError):
            question.clean()

    def test_open_question_cannot_have_choices(self):
        module = Module.objects.create(
            title="Open Module",
            category=Module.CATEGORY_WORKFORCE,
        )
        question = QuizQuestion.objects.create(
            module=module,
            prompt="Explain this",
            qtype=QuizQuestion.QTYPE_OPEN,
        )
        QuizAnswer.objects.create(question=question, text="Choice", is_correct=True)
        with self.assertRaises(ValidationError):
            question.clean()

    def test_convert_legacy_module_quizzes_command(self):
        module = Module.objects.create(
            title="Legacy Command Module",
            category=Module.CATEGORY_WORKFORCE,
            quiz_data={
                "questions": [
                    {
                        "prompt": "Pick yes",
                        "choices": [
                            {"text": "Yes", "is_correct": True},
                            {"text": "No", "is_correct": False},
                        ],
                    }
                ]
            },
        )
        out = StringIO()
        call_command("convert_legacy_module_quizzes", module_id=module.id, stdout=out)
        module.refresh_from_db()
        self.assertEqual(module.questions.count(), 1)
        self.assertIn("Converted 1 questions across 1 module(s).", out.getvalue())


class ResourceDirectoryZipMatchingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not settings.USE_GIS or Point is None:
            raise cls.skipTest("GIS is disabled in this environment.")

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
