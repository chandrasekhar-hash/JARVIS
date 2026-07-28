import time
import uuid
import secrets
import base64
import logging
from typing import Optional, Dict, Any, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import jwt

from config.settings import cloud_settings
from models.schemas import CloudSession, TokenPair, SessionStatus, DeviceTrustState
from repositories.device_repository import device_repo
from repositories.session_repository import session_repo
from repositories.audit_repository import audit_repo

logger = logging.getLogger("JARVIS_Cloud")

class SecurityService:
    def create_auth_challenge(self, device_id: str) -> Dict[str, Any]:
        challenge_id = f"chl_{uuid.uuid4().hex[:16]}"
        nonce = secrets.token_hex(16)
        expires_at = time.time() + 300  # 5 minutes
        return {
            "challenge_id": challenge_id,
            "device_id": device_id,
            "nonce": nonce,
            "expires_at": expires_at
        }

    def verify_ed25519_signature(self, public_key_pem: str, message: bytes, signature_b64: str) -> bool:
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                logger.error("Public key is not Ed25519PublicKey")
                return False
            sig_bytes = base64.b64decode(signature_b64)
            public_key.verify(sig_bytes, message)
            return True
        except Exception as e:
            logger.error(f"Ed25519 verification failed: {e}")
            return False

    def authenticate_device(
        self,
        device_id: str,
        nonce: str,
        signature_b64: str,
        ip_address: str = "127.0.0.1",
        user_agent: str = "JARVIS Cloud Client"
    ) -> Optional[TokenPair]:
        device = device_repo.get_device(device_id)
        if not device:
            audit_repo.log_event("AUTH_FAILED", "device_auth", "failed", device_id=device_id, details={"reason": "Device not found"})
            return None

        if device.trust_state == DeviceTrustState.REVOKED:
            audit_repo.log_event("AUTH_FAILED", "device_auth", "failed", device_id=device_id, details={"reason": "Device revoked"})
            return None

        message_bytes = nonce.encode("utf-8")
        is_valid = self.verify_ed25519_signature(device.public_key, message_bytes, signature_b64)
        if not is_valid:
            audit_repo.log_event("AUTH_FAILED", "device_auth", "failed", device_id=device_id, details={"reason": "Invalid Ed25519 signature"})
            return None

        # Issue Session Tokens
        session_id = f"ses_{uuid.uuid4().hex[:16]}"
        now = time.time()
        access_expire = now + (cloud_settings.access_token_expire_minutes * 60)
        refresh_expire = now + (cloud_settings.refresh_token_expire_days * 86400)

        access_payload = {
            "sub": device.user_id,
            "dev": device_id,
            "ses": session_id,
            "exp": int(access_expire),
            "iat": int(now),
            "iss": cloud_settings.app_name
        }
        access_token = jwt.encode(access_payload, cloud_settings.jwt_secret, algorithm=cloud_settings.jwt_algorithm)
        refresh_token = f"rtk_{secrets.token_urlsafe(32)}"

        session = CloudSession(
            session_id=session_id,
            user_id=device.user_id,
            device_id=device_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=access_expire,
            refresh_expires_at=refresh_expire,
            created_at=now,
            status=SessionStatus.ACTIVE,
            ip_address=ip_address,
            user_agent=user_agent
        )
        session_repo.save_session(session)
        audit_repo.log_event("AUTH_SUCCESS", "device_auth", "success", user_id=device.user_id, device_id=device_id)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=int(cloud_settings.access_token_expire_minutes * 60)
        )

    def refresh_access_token(self, refresh_token: str) -> Optional[TokenPair]:
        session = session_repo.get_session_by_refresh_token(refresh_token)
        if not session or session.status != SessionStatus.ACTIVE:
            return None

        if time.time() > session.refresh_expires_at:
            session_repo.update_session_status(session.session_id, SessionStatus.EXPIRED)
            return None

        now = time.time()
        access_expire = now + (cloud_settings.access_token_expire_minutes * 60)
        access_payload = {
            "sub": session.user_id,
            "dev": session.device_id,
            "ses": session.session_id,
            "exp": int(access_expire),
            "iat": int(now),
            "iss": cloud_settings.app_name
        }
        new_access_token = jwt.encode(access_payload, cloud_settings.jwt_secret, algorithm=cloud_settings.jwt_algorithm)
        session.access_token = new_access_token
        session.expires_at = access_expire
        session_repo.save_session(session)

        return TokenPair(
            access_token=new_access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=int(cloud_settings.access_token_expire_minutes * 60)
        )

    def revoke_session(self, session_id: str) -> bool:
        success = session_repo.update_session_status(session_id, SessionStatus.REVOKED)
        if success:
            audit_repo.log_event("SESSION_REVOKED", "revoke_session", "success", details={"session_id": session_id})
        return success

    def validate_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, cloud_settings.jwt_secret, algorithms=[cloud_settings.jwt_algorithm])
            session = session_repo.get_session_by_token(token)
            if not session or session.status != SessionStatus.ACTIVE:
                return None
            return payload
        except Exception:
            return None

security_service = SecurityService()
