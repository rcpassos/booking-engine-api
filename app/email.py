import smtplib
from email.mime.text import MIMEText
from app.config import settings


def send_recovery_email(to_email: str, token: str) -> None:
    reset_link = f"https://your-domain.com/reset-password?token={token}"
    body = f"Click to reset your password: {reset_link}"
    msg = MIMEText(body)
    msg["Subject"] = "Booking Engine - Password Recovery"
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_pass)
        server.send_message(msg)
