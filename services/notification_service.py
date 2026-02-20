"""Notification delivery service for email messages with optional attachments."""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.settings import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME, SMTP_FROM_EMAIL


def send_email(to_emails: list[str], subject: str, body_text: str,
               attachments: list[tuple[str, bytes, str]] | None = None) -> tuple[bool, str]:
    """Send an email to one or more recipients.

    attachments: list of (filename, bytes, mime_type)
    """
    recipients = [e.strip().lower() for e in (to_emails or []) if e and e.strip()]
    if not recipients:
        return False, "No recipients provided"

    if not SMTP_USER or not SMTP_PASSWORD:
        # Dev fallback: log to console so scheduling workflows still run visibly.
        print(f"[EMAIL PREVIEW] To: {', '.join(recipients)} | Subject: {subject}\n{body_text}")
        return True, "Email preview logged (SMTP not configured)."

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))

        for filename, payload, mime_type in (attachments or []):
            part = MIMEApplication(payload, Name=filename)
            part["Content-Disposition"] = f'attachment; filename="{filename}"'
            part["Content-Type"] = mime_type
            msg.attach(part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, recipients, msg.as_string())
        return True, "Email sent"
    except Exception as e:
        return False, str(e)
