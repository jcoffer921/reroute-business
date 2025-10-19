from django import template

register = template.Library()

@register.filter
def replace_underscore(value):
    if isinstance(value, str):
        return value.replace("_", " ").title()
    return value
