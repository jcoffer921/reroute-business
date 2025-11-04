# resources/views.py
from django.shortcuts import render
from reroute_business.blog.models import BlogPost
from .models import LearningModule


def resource_list(request):
    """
    Render the Resources landing page.
    Includes the Learning Modules section: we query all modules and order by
    most recent (created_at descending) so fresh content appears first.
    """
    modules = LearningModule.objects.all().order_by('-created_at')
    return render(request, 'resources/resource_list.html', {
        'modules': modules,
    })


def interview_prep(request):
    return render(request, 'resources/job_tools/interview_prep.html')

def email_guidance(request):
    return render(request, 'resources/job_tools/email_guidance.html')

def legal_aid(request):
    related_articles = BlogPost.objects.filter(category='legal', published=True).order_by('-created_at')[:3]
    return render(request, 'resources/reentry_help/legal_aid.html', {
        'related_articles': related_articles
    })

def housing(request):
    return render(request, 'resources/reentry_help/housing.html')

def counseling(request):
    return render(request, 'resources/reentry_help/counseling.html')

def tech_courses(request):
    return render(request, 'resources/job_tools/tech_courses.html')

def job_tools_index(request):
    return render(request, 'resources/job_tools/index.html')

def reentry_help_index(request):
    return render(request, 'resources/reentry_help/index.html')
