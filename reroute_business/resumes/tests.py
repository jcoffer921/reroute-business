import json

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from reroute_business.resumes.models import Resume, Experience, Education, EducationType, ResumeSkill


class ResumeBuilderFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass123", email="test@example.com")
        self.client.login(username="tester", password="pass123")

        EducationType.objects.get_or_create(name="HS Diploma/GED", defaults={"order": 0})

    def test_basics_autosave_creates_resume_and_contact(self):
        url = reverse("resumes:resume_basics_autosave")
        payload = {
            "full_name": "Alex Rivera",
            "email": "alex@example.com",
            "phone": "(215) 555-0199",
            "city": "Philadelphia",
            "state": "PA",
            "headline": "Reliable team member",
        }
        res = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        resume = Resume.objects.get(user=self.user, is_imported=False)
        self.assertTrue(resume.step_basics_complete)
        self.assertEqual(resume.headline, "Reliable team member")
        self.assertTrue(resume.contact_info.phone.isdigit())

    def test_experience_autosave_marks_complete(self):
        resume = Resume.objects.create(user=self.user, is_imported=False)
        url = reverse("resumes:resume_experience_autosave")
        payload = {
            "roles": [
                {
                    "job_title": "Warehouse Associate",
                    "company": "Keystone",
                    "start_year": "2022",
                    "end_year": "2024",
                    "responsibilities": "Loaded orders\nTrained staff",
                    "currently_work_here": False,
                }
            ]
        }
        res = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        resume.refresh_from_db()
        self.assertTrue(resume.step_experience_complete)
        self.assertEqual(Experience.objects.filter(resume=resume).count(), 1)

    def test_skills_autosave_persists_categories(self):
        resume = Resume.objects.create(user=self.user, is_imported=False)
        url = reverse("resumes:resume_skills_autosave")
        payload = {"technical": ["Forklift"], "soft": ["Teamwork"]}
        res = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ResumeSkill.objects.filter(resume=resume).count(), 2)

    def test_review_reorder_persists_order(self):
        resume = Resume.objects.create(user=self.user, is_imported=False)
        exp1 = Experience.objects.create(resume=resume, job_title="A", company="Co", order=0)
        exp2 = Experience.objects.create(resume=resume, job_title="B", company="Co", order=1)
        edu_type = EducationType.objects.first()
        edu1 = Education.objects.create(resume=resume, education_type=edu_type, school="School A", order=0)
        edu2 = Education.objects.create(resume=resume, education_type=edu_type, school="School B", order=1)

        url = reverse("resumes:resume_review_reorder")
        payload = {
            "section_order": ["skills", "experience", "basics", "education"],
            "experience_order": [str(exp2.id), str(exp1.id)],
            "education_order": [str(edu2.id), str(edu1.id)],
        }
        res = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)

        resume.refresh_from_db()
        self.assertEqual(resume.section_order, ["skills", "experience", "basics", "education"])
        exp1.refresh_from_db()
        exp2.refresh_from_db()
        edu1.refresh_from_db()
        edu2.refresh_from_db()
        self.assertEqual(exp2.order, 0)
        self.assertEqual(exp1.order, 1)
        self.assertEqual(edu2.order, 0)
        self.assertEqual(edu1.order, 1)
