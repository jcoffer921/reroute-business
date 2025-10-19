from django.test import TestCase
from django.contrib.auth.models import User
from resumes.models import Resume
from job_list.models import Job
from core.models import Skill
from job_list.matching import match_jobs_for_user

class JobMatchingTest(TestCase):
    def setUp(self):
        # Create user and resume
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.resume = Resume.objects.create(user=self.user)

        # Create employer for job postings
        self.employer = User.objects.create_user(username='employer', password='testpass')

        # Create and fetch skills from DB to ensure they are saved properly
        Skill.objects.bulk_create([
            Skill(name="Plumbing"),
            Skill(name="Customer Service"),
        ])
        self.skill1 = Skill.objects.get(name="Plumbing")
        self.skill2 = Skill.objects.get(name="Customer Service")

        # Assign M2M relationship using Skill instances
        self.resume.skills.set([self.skill1])

        # Create jobs with required fields
        self.job1 = Job.objects.create(
            title="Maintenance Tech",
            description="desc",
            requirements="req",
            location="NY",
            employer=self.employer,
            tags="plumbing",
        )
        self.job2 = Job.objects.create(
            title="Retail Associate",
            description="desc",
            requirements="req",
            location="NY",
            employer=self.employer,
            tags="retail",
        )

        # Assign job skills
        self.job1.skills_required.set([self.skill1])
        self.job2.skills_required.set([self.skill2])

    def test_match_jobs_for_user_returns_correct_jobs(self):
        matched_jobs = match_jobs_for_user(self.user)

        self.assertIn(self.job1, matched_jobs)
        self.assertNotIn(self.job2, matched_jobs)

    def test_match_jobs_returns_empty_when_no_resume(self):
        user_no_resume = User.objects.create_user(username='norseeker', password='testpass')
        matched_jobs = match_jobs_for_user(user_no_resume)
        self.assertEqual(matched_jobs, [])

    def test_match_jobs_returns_empty_when_no_skills(self):
        user_no_skills = User.objects.create_user(username='noskills', password='testpass')
        Resume.objects.create(user=user_no_skills)
        matched_jobs = match_jobs_for_user(user_no_skills)
        self.assertEqual(matched_jobs, [])

    def test_match_jobs_orders_by_skill_overlap(self):
        # Add an additional skill to the user's resume
        self.resume.skills.set([self.skill1, self.skill2])

        # Job requiring both skills should rank highest
        job3 = Job.objects.create(
            title="Team Lead",
            description="desc",
            requirements="req",
            location="NY",
            employer=self.employer,
            tags="lead",
        )
        job3.skills_required.set([self.skill1, self.skill2])

        matched_jobs = match_jobs_for_user(self.user)
        self.assertEqual(matched_jobs, [job3, self.job1, self.job2])

