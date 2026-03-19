from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from reroute_business.resources.models import Module, ModuleAttempt, ModuleResponse, QuizAnswer, QuizQuestion


class LearningAdminTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username="staffer",
            email="staff@example.com",
            password="safe-password-123",
            is_staff=True,
        )
        self.client.login(username="staffer", password="safe-password-123")

    def test_content_detail_shows_hardest_questions_from_module_responses(self):
        module = Module.objects.create(
            title="Admin Analytics Module",
            category=Module.CATEGORY_WORKFORCE,
        )
        question = QuizQuestion.objects.create(
            module=module,
            prompt="Tough question",
            order=1,
        )
        wrong_answer = QuizAnswer.objects.create(question=question, text="Wrong", is_correct=False)
        attempt = ModuleAttempt.objects.create(module=module, score=0, total_questions=1)
        ModuleResponse.objects.create(
            attempt=attempt,
            question=question,
            question_identifier=str(question.id),
            selected_answer=wrong_answer,
            is_correct=False,
        )

        response = self.client.get(reverse("admin_portal:content_detail", args=[module.id]))
        self.assertEqual(response.status_code, 200)
        hardest = list(response.context["hardest_questions"])
        self.assertEqual(hardest[0]["question__prompt"], question.prompt)
        self.assertEqual(hardest[0]["miss_count"], 1)

    def test_convert_legacy_quiz_creates_relational_questions(self):
        module = Module.objects.create(
            title="Legacy Quiz Module",
            category=Module.CATEGORY_WORKFORCE,
            quiz_data={
                "questions": [
                    {
                        "prompt": "Pick one",
                        "explanation": "Because it is the best option.",
                        "choices": [
                            {"text": "Yes", "is_correct": True},
                            {"text": "No", "is_correct": False},
                        ],
                    }
                ]
            },
        )

        response = self.client.post(
            reverse("admin_portal:content_convert_legacy_quiz", args=[module.id]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        question = module.questions.get()
        self.assertEqual(question.prompt, "Pick one")
        self.assertEqual(question.explanation, "Because it is the best option.")
        self.assertEqual(question.answers.count(), 2)
        self.assertTrue(question.answers.filter(is_correct=True).exists())
