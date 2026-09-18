"""Sends the HTML digest via Gmail SMTP using an App Password.

Supports multiple recipients: set TO_EMAIL as a comma-separated list in your
GitHub Actions secret, e.g. alice@gmail.com,bob@gmail.com

Credentials are read from environment variables (set as GitHub Actions
encrypted secrets) — never hardcoded, never committed.
"""

import smtplib
import ssl
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def send_email(html_body: str) -> bool:
    if not (config.EMAIL_FROM and config.EMAIL_APP_PASSWORD and config.EMAIL_TO_LIST):
        print(
            "Email credentials not set "
            "(GMAIL_USER / GMAIL_APP_PASSWORD / TO_EMAIL). "
            "Skipping email send."
        )
        return False

    recipients = config.EMAIL_TO_LIST   # list of addresses

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📋 Daily Job Digest — {datetime.date.today().strftime('%d %b %Y')}"
    msg["From"]    = config.EMAIL_FROM
    msg["To"]      = ", ".join(recipients)   # RFC 2822 multi-recipient header
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(context=context)
            server.login(config.EMAIL_FROM, config.EMAIL_APP_PASSWORD)
            # Pass the list so SMTP delivers to every address
            server.sendmail(config.EMAIL_FROM, recipients, msg.as_string())
        print(f"Email sent to: {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False
