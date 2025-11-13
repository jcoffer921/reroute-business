import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Module, QuizQuestion, QuizAnswer, ModuleQuizScore


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
