from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from reroute_business.resumes.models import Resume, ContactInfo, Experience, Education, EducationType, ResumeSkill
from reroute_business.core.models import Skill


class Command(BaseCommand):
    help = "Seed sample resume data for local development."

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            username="resume_demo",
            defaults={"email": "resume_demo@example.com", "first_name": "Jordan", "last_name": "Reed"},
        )

        resume = Resume.objects.filter(user=user, is_imported=False).first()
        if not resume:
            resume = Resume.objects.create(
                user=user,
                is_imported=False,
                full_name="Jordan Reed",
                headline="Reliable team member with hands-on operations experience",
                section_order=["basics", "experience", "skills", "education"],
                step_basics_complete=True,
                step_experience_complete=True,
                step_skills_complete=True,
                step_education_complete=True,
                step_review_complete=False,
            )

        ContactInfo.objects.update_or_create(
            resume=resume,
            defaults={
                "full_name": "Jordan Reed",
                "email": "resume_demo@example.com",
                "phone": "2155550189",
                "city": "Philadelphia",
                "state": "PA",
            },
        )

        Experience.objects.filter(resume=resume).delete()
        Experience.objects.create(
            resume=resume,
            role_type="job",
            job_title="Warehouse Associate",
            company="Keystone Logistics",
            start_year="2021",
            end_year="2024",
            responsibilities="Loaded outbound orders with 99% accuracy.\nTrained new hires on safety protocols.",
            tools="Pallet jack, RF scanner",
            order=0,
        )
        Experience.objects.create(
            resume=resume,
            role_type="other",
            job_title="Workforce Training Program",
            company="ReEntry Skills Initiative",
            start_year="2020",
            end_year="2021",
            responsibilities="Completed forklift certification.\nLed small group projects.",
            tools="Forklift",
            order=1,
        )

        Education.objects.filter(resume=resume).delete()
        hs_type, _ = EducationType.objects.get_or_create(name="HS Diploma/GED", defaults={"order": 0})
        Education.objects.create(
            resume=resume,
            education_type=hs_type,
            school="Central High School",
            year="2016",
            details="GED with honors",
            order=0,
        )

        ResumeSkill.objects.filter(resume=resume).delete()
        resume.skills.clear()
        technical = ["Forklift Operation", "Inventory Control", "Safety Compliance"]
        soft = ["Teamwork", "Reliability", "Communication"]
        for idx, name in enumerate(technical):
            skill, _ = Skill.objects.get_or_create(name=name.lower())
            resume.skills.add(skill)
            ResumeSkill.objects.create(resume=resume, skill=skill, category="technical", order=idx)
        for idx, name in enumerate(soft):
            skill, _ = Skill.objects.get_or_create(name=name.lower())
            resume.skills.add(skill)
            ResumeSkill.objects.create(resume=resume, skill=skill, category="soft", order=idx)

        self.stdout.write(self.style.SUCCESS("Seeded resume_demo resume data."))
