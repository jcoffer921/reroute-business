# main/templatetags/custom_filters.py
# ------------------------------------------------------------
# Custom template filters for role checks. Importable in
# templates via:  {% load roles %}
#
# Usage examples in templates:
#   {% if user|has_group:'Employer' %} ... {% endif %}
#   {% if user|is_employer %} ... {% endif %}
# ------------------------------------------------------------
from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Returns True if the user is in the given group.
    Usage in templates:
      {% if user|has_group:"Employer" %} ... {% endif %}
    """
    if not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name=group_name).exists()
