# ------------------------------------------------------------
# Lightweight widget-tweaks: add_class and attr filters
# Usage in templates:
#   {% load form_extras %}
#   {{ form.email|add_class:"input"|attr:"autocomplete=email"|attr:"placeholder=name@company.com" }}
#
# Both filters work on:
#  - BoundField objects (preferred)
#  - Already-rendered HTML strings (fallback: injects attributes into the tag)
# ------------------------------------------------------------
from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

def _merge_class(existing: str, new: str) -> str:
    existing = (existing or "").strip()
    new = (new or "").strip()
    if not existing:
        return new
    # Avoid duplicates while keeping order
    seen = []
    for c in (existing + " " + new).split():
        if c not in seen:
            seen.append(c)
    return " ".join(seen)

@register.filter(name="add_class")
def add_class(field, css_classes: str):
    """
    Append CSS classes to a field. Chainable with |attr.
    Works on BoundField and rendered HTML.
    """
    # Case 1: BoundField (best path)
    if hasattr(field, "as_widget") and hasattr(field, "field"):
        attrs = dict(field.field.widget.attrs)  # copy
        attrs["class"] = _merge_class(attrs.get("class", ""), css_classes)
        return field.as_widget(attrs=attrs)

    # Case 2: Rendered HTML string → inject class attr in the first tag
    html = str(field or "")
    # If class exists, append; otherwise insert
    if 'class="' in html:
        return mark_safe(re.sub(r'class="([^"]*)"', lambda m: f'class="{_merge_class(m.group(1), css_classes)}"', html, count=1))
    return mark_safe(re.sub(r"(<\w+)(\s|>)", rf'\1 class="{css_classes}"\2', html, count=1))

@register.filter(name="attr")
def attr(field, arg: str):
    """
    Set a single attribute via "key=value" (e.g., "autocomplete=email").
    Chainable: {{ field|attr:"autocomplete=email"|attr:"inputmode=email" }}
    Works on BoundField and rendered HTML.
    """
    if not isinstance(arg, str) or "=" not in arg:
        return field
    key, value = arg.split("=", 1)

    # Case 1: BoundField
    if hasattr(field, "as_widget") and hasattr(field, "field"):
        attrs = dict(field.field.widget.attrs)
        if key == "class":
            attrs["class"] = _merge_class(attrs.get("class", ""), value)
        else:
            attrs[key] = value
        return field.as_widget(attrs=attrs)

    # Case 2: Rendered HTML string
    html = str(field or "")
    # If attribute exists, replace its value; else insert into opening tag
    pattern = re.compile(rf'(\s{re.escape(key)}=")([^"]*)(")')
    if pattern.search(html):
        return mark_safe(pattern.sub(rf'\1{value}\3', html, count=1))
    return mark_safe(re.sub(r"(<\w+)(\s|>)", rf'\1 {key}="{value}"\2', html, count=1))
