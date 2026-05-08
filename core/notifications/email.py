import logging
from email.utils import formataddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def send_email(
    *,
    subject: str,
    to: list[str],
    body: str,
    html_body: str | None = None,
    from_email: str | None = None,
    from_name: str | None = None,
) -> int:
    if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER:
        logger.warning("email: EMAIL_HOST/EMAIL_HOST_USER not set; skip")
        return 0

    sender = from_email or settings.DEFAULT_FROM_EMAIL
    if from_name:
        sender = formataddr((from_name, sender))

    msg = EmailMultiAlternatives(subject=subject, body=body, from_email=sender, to=to)
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    return msg.send(fail_silently=False)
