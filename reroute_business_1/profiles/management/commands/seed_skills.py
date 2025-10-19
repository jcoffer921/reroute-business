# data/seed_skills.py

from django.core.management.base import BaseCommand
from reroute_business.profiles.models import Skill

class Command(BaseCommand):
    help = "Seed the database with common soft and hard skills."

    def handle(self, *args, **kwargs):
        skill_names = [
            # Hard Skills
            "Construction", "Painting", "Plumbing", "Electrical Work", "Welding", "Drywall",
            "Landscaping", "Carpentry", "Demolition", "Forklift Operation", "Warehouse Management",
            "Machinery Operation", "HVAC", "Roofing", "Power Tools", "Auto Repair", "Assembly Line Work",
            "Cleaning", "Janitorial Work", "Maintenance", "Sanitation", "Waste Management",
            "Cooking", "Food Preparation", "Dishwashing", "Customer Service", "Catering", "Barista",
            "Cashiering", "Stocking", "Shelf Organization", "Delivery Driving", "Loading and Unloading",
            "Inventory Management", "Order Picking", "Packaging", "Shipping and Receiving",
            "OSHA Certified", "CPR Certified", "First Aid", "ServSafe", "DOT Compliance",

            # Soft Skills
            "Time Management", "Teamwork", "Punctuality", "Problem Solving", "Adaptability",
            "Work Ethic", "Communication", "Conflict Resolution", "Attention to Detail",
            "Reliability", "Accountability", "Respectfulness", "Following Instructions",
            "Motivation", "Leadership", "Stress Management", "Organization", "Empathy",
            "Critical Thinking", "Positive Attitude", "Flexibility", "Multi-tasking"
        ]

        skills_to_create = [Skill(name=name) for name in skill_names if not Skill.objects.filter(name=name).exists()]
        Skill.objects.bulk_create(skills_to_create)

        self.stdout.write(self.style.SUCCESS(f"{len(skills_to_create)} new skills added."))
