# resumes/utils/cleaners.py
import re


def clean_bullet(text):
    return re.sub(r'^[•\-\*\–]\s*', '', text).strip()


