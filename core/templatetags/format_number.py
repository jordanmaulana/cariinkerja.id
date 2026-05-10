from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

from jobs.consts import JobType, RemoteOption

register = template.Library()


@register.filter
def intdot(value):
    if value is None or value == "" or value == 0:
        return "0"
    try:
        return f"{intcomma(int(value)).replace(',', '.')}"
    except (ValueError, TypeError):
        return "0"


_CHOICE_MAPS = {
    "job_type": dict(JobType.choices),
    "remote_option": dict(RemoteOption.choices),
}


@register.filter
def display_choices(values, choices_name):
    mapping = _CHOICE_MAPS.get(choices_name, {})
    if not values:
        return "—"
    return ", ".join(mapping.get(v, v) for v in values)
