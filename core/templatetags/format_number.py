from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter
def intdot(value):
    if value is None or value == "" or value == 0:
        return "0"
    try:
        return f"{intcomma(int(value)).replace(',', '.')}"
    except (ValueError, TypeError):
        return "0"
