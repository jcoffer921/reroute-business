from django import template

from reroute_business.job_list.models import Job

register = template.Library()


@register.simple_tag
def reports_flags_count():
    try:
        return Job.objects.filter(is_flagged=True).count()
    except Exception:
        return 0
