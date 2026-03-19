from django.db import transaction

from reroute_business.resources.models import QuizAnswer, QuizQuestion


def convert_module_legacy_quiz(module):
    quiz_data = module.quiz_data or {}
    raw_questions = quiz_data.get("questions") if isinstance(quiz_data, dict) else None
    if not isinstance(raw_questions, list) or not raw_questions:
        return 0

    created_count = 0
    with transaction.atomic():
        for idx, raw in enumerate(raw_questions, 1):
            if not isinstance(raw, dict):
                continue
            prompt = (raw.get("prompt") or "").strip()
            if not prompt:
                continue
            question = QuizQuestion.objects.create(
                module=module,
                prompt=prompt,
                explanation=(raw.get("explanation") or "").strip(),
                order=int(raw.get("order") or idx),
                qtype=QuizQuestion.QTYPE_MULTIPLE_CHOICE,
            )
            for choice in raw.get("choices") or []:
                if not isinstance(choice, dict):
                    continue
                text = (choice.get("text") or "").strip()
                if not text:
                    continue
                QuizAnswer.objects.create(
                    question=question,
                    text=text,
                    is_correct=bool(choice.get("is_correct") or choice.get("correct")),
                )
            created_count += 1
    return created_count
