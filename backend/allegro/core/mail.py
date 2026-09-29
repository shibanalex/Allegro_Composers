"""Sending e-mail through an SMTP server (Yandex Mail with an application password, or any other).

Without SMTP_HOST the site sends no mail at all, and the e-mail options are hidden on the site.
"""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from allegro.core.config import settings


def mail_enabled() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def send_mail(to: str, subject: str, text: str, html: str | None = None) -> None:
    """Blocking: call it from a worker thread, never from a request"""
    message = EmailMessage()
    message["From"] = formataddr((settings.mail_from_name, settings.mail_from or settings.smtp_user))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")
    context = ssl.create_default_context()
    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=20) as smtp:
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls(context=context)
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
