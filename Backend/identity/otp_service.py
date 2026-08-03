import time
import secrets
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("jarvis_otp")

OTP_EXPIRY_SECONDS = 600       # 10 minutes
MAX_VERIFICATION_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 30
VERIFICATION_TOKEN_EXPIRY = 900 # 15 minutes

class OTPService:
    """
    Cryptographically Secure In-Memory OTP Engine for J.A.R.V.I.S.
    Handles OTP generation, hashing, rate-limiting, verification, and token issuance.
    """

    def __init__(self):
        # Email -> OTP Record
        self._otp_store: Dict[str, Dict[str, Any]] = {}
        # Verification Token -> Token Record
        self._verification_tokens: Dict[str, Dict[str, Any]] = {}
        # Reset Token -> Token Record
        self._reset_tokens: Dict[str, Dict[str, Any]] = {}

    def _hash_otp(self, otp: str) -> str:
        return hashlib.sha256(otp.encode("utf-8")).hexdigest()

    def generate_registration_otp(self, email: str) -> Tuple[str, Optional[str]]:
        """
        Generates a secure 6-digit OTP for registration.
        Invalidates any existing OTP for the email.
        Enforces a 30-second resend cooldown.
        Returns (otp, error_message).
        """
        clean_email = email.strip().lower()
        now = time.time()

        # Check resend cooldown
        if clean_email in self._otp_store:
            last_sent = self._otp_store[clean_email].get("last_sent_at", 0)
            elapsed = now - last_sent
            if elapsed < RESEND_COOLDOWN_SECONDS:
                remaining = int(RESEND_COOLDOWN_SECONDS - elapsed)
                return "", f"Please wait {remaining} seconds before requesting a new code."

        # Cryptographically secure 6-digit OTP
        otp = f"{secrets.randbelow(900000) + 100000:06d}"
        otp_hash = self._hash_otp(otp)

        # Store hashed OTP and overwrite previous OTP immediately
        self._otp_store[clean_email] = {
            "otp_hash": otp_hash,
            "expires_at": now + OTP_EXPIRY_SECONDS,
            "attempts": 0,
            "last_sent_at": now,
            "purpose": "registration"
        }

        logger.info(f"[OTPService] Generated new registration OTP for {clean_email} (Expires in 10m)")
        return otp, None

    def verify_registration_otp(self, email: str, user_otp: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifies the user-entered OTP for registration.
        Returns (success, verification_token, error_message).
        """
        clean_email = email.strip().lower()
        clean_otp = user_otp.strip()
        now = time.time()

        if len(clean_otp) != 6 or not clean_otp.isdigit():
            return False, None, "Please enter all 6 digits."

        record = self._otp_store.get(clean_email)
        if not record or record.get("purpose") != "registration":
            return False, None, "No active verification code found. Please request a new code."

        # Check expiry
        if now > record["expires_at"]:
            del self._otp_store[clean_email]
            return False, None, "Verification code has expired. Please request a new code."

        # Check attempt limits
        if record["attempts"] >= MAX_VERIFICATION_ATTEMPTS:
            del self._otp_store[clean_email]
            return False, None, "Maximum verification attempts exceeded. Please request a new code."

        # Compare OTP hash
        user_hash = self._hash_otp(clean_otp)
        if user_hash != record["otp_hash"]:
            record["attempts"] += 1
            remaining = MAX_VERIFICATION_ATTEMPTS - record["attempts"]
            if remaining <= 0:
                del self._otp_store[clean_email]
                return False, None, "Maximum verification attempts exceeded. Please request a new code."
            return False, None, f"Invalid verification code. {remaining} attempt(s) remaining."

        # Successful verification: invalidate OTP record immediately
        del self._otp_store[clean_email]

        # Issue short-lived verification token for completing registration
        token = secrets.token_urlsafe(32)
        self._verification_tokens[token] = {
            "email": clean_email,
            "expires_at": now + VERIFICATION_TOKEN_EXPIRY
        }

        logger.info(f"[OTPService] Registration OTP successfully verified for {clean_email}")
        return True, token, None

    def consume_verification_token(self, token: str, email: str) -> bool:
        """
        Validates and consumes a verification token for account creation.
        """
        clean_email = email.strip().lower()
        now = time.time()

        record = self._verification_tokens.get(token)
        if not record:
            return False

        if record["email"] != clean_email or now > record["expires_at"]:
            del self._verification_tokens[token]
            return False

        # Consume token immediately so it cannot be reused
        del self._verification_tokens[token]
        return True

    # --- FORGOT PASSWORD OTP METHODS ---

    def generate_password_reset_otp(self, email: str) -> Tuple[str, Optional[str]]:
        """
        Generates a secure 6-digit OTP for password reset.
        Invalidates any existing OTP for the email.
        Enforces a 30-second resend cooldown.
        Returns (otp, error_message).
        """
        clean_email = email.strip().lower()
        now = time.time()

        # Check resend cooldown
        if clean_email in self._otp_store:
            last_sent = self._otp_store[clean_email].get("last_sent_at", 0)
            elapsed = now - last_sent
            if elapsed < RESEND_COOLDOWN_SECONDS:
                remaining = int(RESEND_COOLDOWN_SECONDS - elapsed)
                return "", f"Please wait {remaining} seconds before requesting a new code."

        # Cryptographically secure 6-digit OTP
        otp = f"{secrets.randbelow(900000) + 100000:06d}"
        otp_hash = self._hash_otp(otp)

        # Store hashed OTP and overwrite previous OTP immediately
        self._otp_store[clean_email] = {
            "otp_hash": otp_hash,
            "expires_at": now + OTP_EXPIRY_SECONDS,
            "attempts": 0,
            "last_sent_at": now,
            "purpose": "password_reset"
        }

        logger.info(f"[OTPService] Generated new password reset OTP for {clean_email} (Expires in 10m)")
        return otp, None

    def verify_password_reset_otp(self, email: str, user_otp: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifies the user-entered OTP for password reset.
        Returns (success, reset_token, error_message).
        """
        clean_email = email.strip().lower()
        clean_otp = user_otp.strip()
        now = time.time()

        if len(clean_otp) != 6 or not clean_otp.isdigit():
            return False, None, "Please enter all 6 digits."

        record = self._otp_store.get(clean_email)
        if not record or record.get("purpose") != "password_reset":
            return False, None, "No active verification code found. Please request a new code."

        # Check expiry
        if now > record["expires_at"]:
            del self._otp_store[clean_email]
            return False, None, "Verification code has expired. Please request a new code."

        # Check attempt limits
        if record["attempts"] >= MAX_VERIFICATION_ATTEMPTS:
            del self._otp_store[clean_email]
            return False, None, "Maximum verification attempts exceeded. Please request a new code."

        # Compare OTP hash
        user_hash = self._hash_otp(clean_otp)
        if user_hash != record["otp_hash"]:
            record["attempts"] += 1
            remaining = MAX_VERIFICATION_ATTEMPTS - record["attempts"]
            if remaining <= 0:
                del self._otp_store[clean_email]
                return False, None, "Maximum verification attempts exceeded. Please request a new code."
            return False, None, f"Invalid verification code. {remaining} attempt(s) remaining."

        # Successful verification: invalidate OTP record immediately
        del self._otp_store[clean_email]

        # Issue short-lived password reset token for changing password
        token = secrets.token_urlsafe(32)
        self._reset_tokens[token] = {
            "email": clean_email,
            "expires_at": now + VERIFICATION_TOKEN_EXPIRY
        }

        logger.info(f"[OTPService] Password reset OTP successfully verified for {clean_email}")
        return True, token, None

    def consume_password_reset_token(self, token: str, email: str) -> bool:
        """
        Validates and consumes a single-use password reset token.
        """
        clean_email = email.strip().lower()
        now = time.time()

        record = self._reset_tokens.get(token)
        if not record:
            return False

        if record["email"] != clean_email or now > record["expires_at"]:
            del self._reset_tokens[token]
            return False

        # Consume token immediately so it cannot be reused
        del self._reset_tokens[token]
        return True

otp_service = OTPService()
