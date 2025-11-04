from django.core.management.base import BaseCommand

from reroute_business.resources.models import (
    Lesson,
    LessonQuestion,
    LessonChoice,
)


class Command(BaseCommand):
    help = "Seed the 'Resume Basics 101' interactive lesson with questions and timestamps. Safe to run multiple times."

    def handle(self, *args, **options):
        video_path = "/static/resources/videos/ResumeBasics101-improved.mp4"

        lesson, _ = Lesson.objects.update_or_create(
            slug="resume-basics-101",
            defaults={
                "title": "Resume Basics 101",
                "description": "Build a strong resume by mastering structure, strong statements, and soft skills.",
                "video_static_path": video_path,
                "duration_seconds": 200.0,  # approx; not critical
                "is_active": True,
            },
        )

        # Helper to upsert questions and choices
        def upsert_question(order, timestamp, prompt, qtype, is_scored=True, is_required=True):
            q, _ = LessonQuestion.objects.update_or_create(
                lesson=lesson, order=order,
                defaults={
                    "timestamp_seconds": timestamp,
                    "prompt": prompt,
                    "qtype": qtype,
                    "is_required": is_required,
                    "is_scored": is_scored,
                    "active": True,
                },
            )
            return q

        # Q1 – 0:52
        q1 = upsert_question(
            1, 52.0,
            "Which section should appear first on your résumé?",
            LessonQuestion.TYPE_MULTIPLE_CHOICE,
            is_scored=True,
        )
        LessonChoice.objects.update_or_create(question=q1, label='a', defaults={"text": "Skills", "is_correct": False, "position": 1})
        LessonChoice.objects.update_or_create(question=q1, label='b', defaults={"text": "Contact Information", "is_correct": True,  "position": 2})
        LessonChoice.objects.update_or_create(question=q1, label='c', defaults={"text": "Work Experience", "is_correct": False, "position": 3})
        LessonChoice.objects.update_or_create(question=q1, label='d', defaults={"text": "Education", "is_correct": False, "position": 4})

        # Q2 – 1:22 (82s)
        q2 = upsert_question(
            2, 82.0,
            "Which of these is a stronger way to describe your work?",
            LessonQuestion.TYPE_MULTIPLE_CHOICE,
            is_scored=True,
        )
        LessonChoice.objects.update_or_create(question=q2, label='a', defaults={"text": "Worked at a restaurant", "is_correct": False, "position": 1})
        LessonChoice.objects.update_or_create(question=q2, label='b', defaults={"text": "Served over 50 customers daily while maintaining 100 percent order accuracy", "is_correct": True, "position": 2})

        # Q3 – 1:59 (119s)
        q3 = upsert_question(
            3, 119.0,
            "Why are soft skills important on a résumé?",
            LessonQuestion.TYPE_MULTIPLE_CHOICE,
            is_scored=True,
        )
        LessonChoice.objects.update_or_create(question=q3, label='a', defaults={"text": "They replace work experience", "is_correct": False, "position": 1})
        LessonChoice.objects.update_or_create(question=q3, label='b', defaults={"text": "They take up space", "is_correct": False, "position": 2})
        LessonChoice.objects.update_or_create(question=q3, label='c', defaults={"text": "They are optional", "is_correct": False, "position": 3})
        LessonChoice.objects.update_or_create(question=q3, label='d', defaults={"text": "They show how you work with others", "is_correct": True, "position": 4})

        # Q4 – 2:40 (160s) – Open ended
        upsert_question(
            4, 160.0,
            "Using the formula Action Verb + Task + Result, write one strong sentence for a job or task you’ve done.",
            LessonQuestion.TYPE_OPEN_ENDED,
            is_scored=False,
            is_required=True,
        )

        self.stdout.write(self.style.SUCCESS("Seeded 'Resume Basics 101' lesson."))

