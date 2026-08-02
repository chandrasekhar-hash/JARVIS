import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger("jarvis_email")

class EmailService:
    """
    Centralized Email Delivery Service for JARVIS with production SMTP support
    and Development mode fallback.
    Configured via environment variables:
    - SMTP_HOST
    - SMTP_PORT (default 587)
    - SMTP_USER
    - SMTP_PASSWORD
    - SMTP_FROM_EMAIL
    - JARVIS_ENV (development/test/production)
    """

    def __init__(self):
        self._load_config()

    def _load_config(self):
        self.smtp_host = os.getenv("SMTP_HOST", "").strip()
        port_str = os.getenv("SMTP_PORT", "587").strip()
        self.smtp_port = int(port_str) if port_str.isdigit() else 587
        self.smtp_user = os.getenv("SMTP_USER", "").strip()
        self.smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
        self.from_email = os.getenv("SMTP_FROM_EMAIL", "").strip() or self.smtp_user or "noreply@jarvis.ai"
        self.env = os.getenv("JARVIS_ENV", "development").lower().strip()

    @property
    def is_configured(self) -> bool:
        self._load_config()
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def _dispatch_smtp(self, clean_email: str, msg: MIMEMultipart) -> None:
        self._load_config()
        if self.smtp_port == 465:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15) as server:
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, [clean_email], msg.as_string())
        else:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, [clean_email], msg.as_string())

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Centralized email delivery method for JARVIS system.
        Future JARVIS notifications and email dispatches route through this method.
        """
        clean_email = to_email.strip().lower()
        if not clean_email or "@" not in clean_email:
            raise ValueError(f"Invalid recipient email address: {to_email}")

        plain_text = text_body or "This message was sent by J.A.R.V.I.S."

        if self.is_configured:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = self.from_email
                msg["To"] = clean_email
                msg.attach(MIMEText(plain_text, "plain"))
                msg.attach(MIMEText(html_body, "html"))

                self._dispatch_smtp(clean_email, msg)
                logger.info(f"[EmailService] Real email sent to {clean_email} via SMTP provider.")
                return True
            except Exception as e:
                err_msg = str(e)
                logger.error(f"[EmailService] SMTP email delivery failed for {clean_email}: {err_msg}")
                raise RuntimeError(f"SMTP delivery failed: {err_msg}")

        # Development Fallback Mode (only active when SMTP provider is NOT configured)
        logger.info(f"[EmailService DEV] Simulated email dispatch to {clean_email} | Subject: '{subject}'")
        return True

email_service = EmailService()
