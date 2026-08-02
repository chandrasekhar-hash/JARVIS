import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_dir))

import config
from identity.email_service import email_service

def test_harmless_email_delivery(recipient_email: str):
    print("=== JARVIS EMAIL SERVICE DISPATCH TEST ===")
    print(f"Checking EmailService configuration state...")
    print(f"Is Configured: {email_service.is_configured}")
    print(f"SMTP Host: {email_service.smtp_host}")
    print(f"SMTP Port: {email_service.smtp_port}")
    print(f"SMTP User set: {bool(email_service.smtp_user)}")
    print(f"SMTP Password set: {bool(email_service.smtp_password)}")

    if not email_service.is_configured:
        print("\n[STATUS: WAITING FOR CREDENTIALS]")
        print("SMTP provider credentials are not set in backend/.env.")
        return False

    subject = "JARVIS Email System Test"
    text_body = "JARVIS email delivery is working correctly."
    html_body = """
    <div style="font-family: Arial, sans-serif; background-color: #0c1017; color: #e0f2fe; padding: 24px; border-radius: 8px; max-width: 480px; margin: 0 auto; border: 1px solid rgba(0, 240, 255, 0.2);">
      <h2 style="color: #00ffe1; margin-top: 0; font-size: 20px; letter-spacing: 2px;">J.A.R.V.I.S.</h2>
      <p style="color: #94a3b8; font-size: 14px;">Email Delivery System Test</p>
      <hr style="border: 0; border-top: 1px solid rgba(0, 240, 255, 0.15); margin: 16px 0;" />
      <p style="font-size: 16px; color: #00ffe1;">JARVIS email delivery is working correctly.</p>
      <p style="font-size: 12px; color: #64748b; margin-top: 24px;">Automated system verification email.</p>
    </div>
    """

    print(f"\nAttempting real email delivery to {recipient_email}...")
    try:
        email_service.send_email(recipient_email, subject, html_body, text_body)
        print("\n[STATUS: SUCCESS]")
        print(f"Harmless test email accepted by SMTP provider for delivery to {recipient_email}.")
        return True
    except Exception as e:
        print("\n[STATUS: FAIL]")
        print(f"SMTP Delivery Exception: {e}")
        return False

if __name__ == "__main__":
    recipient = sys.argv[1] if len(sys.argv) > 1 else email_service.smtp_user
    if not recipient:
        recipient = "test@example.com"
    test_harmless_email_delivery(recipient)
