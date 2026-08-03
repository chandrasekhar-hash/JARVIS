import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import httpx
from dotenv import load_dotenv

logger = logging.getLogger("jarvis_email")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

class EmailService:
    """
    Centralized Email Delivery Service for JARVIS supporting Brevo Transactional Email API (REST v3).
    Configured via backend/.env:
    - BREVO_API_KEY
    - BREVO_SENDER_EMAIL
    - BREVO_SENDER_NAME
    """

    def __init__(self):
        self._load_config()

    def _load_config(self):
        backend_dir = Path(__file__).resolve().parent.parent
        backend_env = backend_dir / ".env"
        if backend_env.exists():
            load_dotenv(dotenv_path=backend_env, override=True)

        self.brevo_api_key = os.getenv("BREVO_API_KEY", "").strip()
        self.brevo_sender_email = os.getenv("BREVO_SENDER_EMAIL", "").strip()
        self.brevo_sender_name = os.getenv("BREVO_SENDER_NAME", "JARVIS").strip() or "JARVIS"

    @property
    def is_brevo_configured(self) -> bool:
        self._load_config()
        return bool(self.brevo_api_key and self.brevo_sender_email)

    def send_brevo_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email using Brevo Transactional Email API (REST v3).
        NEVER logs or exposes BREVO_API_KEY or secret headers.
        """
        self._load_config()
        if not self.brevo_api_key:
            raise RuntimeError("Brevo API key is missing or not configured.")
        if not self.brevo_sender_email:
            raise RuntimeError("Brevo sender email is missing or not configured.")

        clean_to_email = to_email.strip().lower()
        if not clean_to_email or "@" not in clean_to_email:
            raise ValueError(f"Invalid recipient email address: {to_email}")

        headers = {
            "accept": "application/json",
            "api-key": self.brevo_api_key,
            "content-type": "application/json"
        }

        payload = {
            "sender": {
                "name": self.brevo_sender_name,
                "email": self.brevo_sender_email
            },
            "to": [
                {"email": clean_to_email}
            ],
            "subject": subject,
            "htmlContent": html_body
        }
        if text_body:
            payload["textContent"] = text_body

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(BREVO_API_URL, headers=headers, json=payload)
                
            if response.status_code in (200, 201, 202):
                res_data = response.json()
                message_id = res_data.get("messageId", "UNKNOWN_MSG_ID")
                logger.info(f"[EmailService] Brevo email sent successfully to {clean_to_email} | MessageID: {message_id}")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "message_id": message_id,
                    "detail": "Email accepted by Brevo API"
                }
            else:
                try:
                    err_json = response.json()
                    err_msg = err_json.get("message") or err_json.get("code") or response.text
                except Exception:
                    err_msg = response.text or f"HTTP {response.status_code}"
                
                logger.error(f"[EmailService] Brevo API Error ({response.status_code}): {err_msg}")
                raise RuntimeError(f"Brevo API delivery failed (Status {response.status_code}): {err_msg}")

        except httpx.TimeoutException:
            logger.error(f"[EmailService] Brevo API connection timed out for {clean_to_email}")
            raise RuntimeError("Unable to send verification code. Connection timed out.")
        except httpx.RequestError as req_err:
            logger.error(f"[EmailService] Brevo API network error: {req_err}")
            raise RuntimeError("Unable to send verification code. Network failure.")

    def send_registration_otp(self, to_email: str, otp: str) -> bool:
        """
        Sends Registration OTP via Brevo Transactional Email API.
        """
        subject = "JARVIS — Verify Your Email"
        
        text_body = (
            "J.A.R.V.I.S.\n\n"
            "EMAIL VERIFICATION\n\n"
            "Your verification code is:\n\n"
            f"{otp}\n\n"
            "This code expires in 10 minutes.\n\n"
            "If you did not request this, ignore this email."
        )

        html_body = (
            "<!DOCTYPE html>"
            "<html><head><meta charset='utf-8'></head>"
            "<body style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #e6edf3; margin: 0; padding: 40px 20px;'>"
            "<div style='max-width: 480px; margin: 0 auto; background-color: #131b2e; border: 1px solid #1f293d; border-radius: 12px; padding: 32px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);'>"
            "<div style='text-align: center; margin-bottom: 24px;'>"
            "<h1 style='color: #00f2fe; margin: 0; font-size: 26px; font-weight: 800; letter-spacing: 3px;'>J.A.R.V.I.S.</h1>"
            "<p style='color: #64748b; margin-top: 6px; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;'>EMAIL VERIFICATION</p>"
            "</div>"
            "<p style='font-size: 15px; color: #cbd5e1; text-align: center; margin-bottom: 8px;'>Your verification code is:</p>"
            "<div style='text-align: center; background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 18px; margin: 20px 0;'>"
            f"<span style='font-family: \"Courier New\", Courier, monospace; font-size: 36px; font-weight: 700; color: #00f2fe; letter-spacing: 8px;'>{otp}</span>"
            "</div>"
            "<p style='font-size: 14px; color: #94a3b8; text-align: center; margin: 0;'>This code expires in <strong>10 minutes</strong>.</p>"
            "<div style='margin-top: 32px; border-top: 1px solid #1e293b; padding-top: 16px; text-align: center;'>"
            "<p style='font-size: 12px; color: #475569; margin: 0;'>If you did not request this, ignore this email.</p>"
            "</div>"
            "</div></body></html>"
        )

        res = self.send_brevo_email(to_email, subject, html_body, text_body)
        return res.get("success", False)

    def send_password_reset_otp(self, to_email: str, otp: str) -> bool:
        """
        Sends Password Reset OTP via Brevo Transactional Email API.
        """
        subject = "JARVIS — Password Reset"

        text_body = (
            "J.A.R.V.I.S.\n\n"
            "PASSWORD RESET\n\n"
            "Your verification code is:\n\n"
            f"{otp}\n\n"
            "This code expires in 10 minutes.\n\n"
            "If you did not request a password reset, ignore this email."
        )

        html_body = (
            "<!DOCTYPE html>"
            "<html><head><meta charset='utf-8'></head>"
            "<body style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #e6edf3; margin: 0; padding: 40px 20px;'>"
            "<div style='max-width: 480px; margin: 0 auto; background-color: #131b2e; border: 1px solid #1f293d; border-radius: 12px; padding: 32px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);'>"
            "<div style='text-align: center; margin-bottom: 24px;'>"
            "<h1 style='color: #00f2fe; margin: 0; font-size: 26px; font-weight: 800; letter-spacing: 3px;'>J.A.R.V.I.S.</h1>"
            "<p style='color: #64748b; margin-top: 6px; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;'>PASSWORD RESET</p>"
            "</div>"
            "<p style='font-size: 15px; color: #cbd5e1; text-align: center; margin-bottom: 8px;'>Your verification code is:</p>"
            "<div style='text-align: center; background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 18px; margin: 20px 0;'>"
            f"<span style='font-family: \"Courier New\", Courier, monospace; font-size: 36px; font-weight: 700; color: #00f2fe; letter-spacing: 8px;'>{otp}</span>"
            "</div>"
            "<p style='font-size: 14px; color: #94a3b8; text-align: center; margin: 0;'>This code expires in <strong>10 minutes</strong>.</p>"
            "<div style='margin-top: 32px; border-top: 1px solid #1e293b; padding-top: 16px; text-align: center;'>"
            "<p style='font-size: 12px; color: #475569; margin: 0;'>If you did not request a password reset, ignore this email.</p>"
            "</div>"
            "</div></body></html>"
        )

        res = self.send_brevo_email(to_email, subject, html_body, text_body)
        return res.get("success", False)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        if self.is_brevo_configured:
            res = self.send_brevo_email(to_email, subject, html_body, text_body)
            return res.get("success", False)
        
        raise RuntimeError("Email provider is not configured.")

email_service = EmailService()
