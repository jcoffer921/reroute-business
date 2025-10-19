from django.http import JsonResponse
from .models import Skill
from .constants import RELATABLE_SKILLS

def suggested_skills(request):
    # Get skills from the database
    db_skills = list(Skill.objects.values_list('name', flat=True))

    # Combine with predefined skills from constants.py
    all_skills = list(set(db_skills + RELATABLE_SKILLS))  # merge and deduplicate

    return JsonResponse(all_skills, safe=False)