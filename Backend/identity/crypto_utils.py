import os
import secrets
import uuid
import hashlib
from typing import Tuple, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from tools.telemetry import log_structured, backend_log
from Backend.security.keystore.keystore_manager import keystore_manager

class CryptoUtils:
    """
    Provides modern cryptography services: Ed25519 key generation & signing via OS KeystoreManager,
    SHA-256 fingerprinting, PBKDF2 password hashing with salt, and secure token generation.
    """

    @staticmethod
    def get_or_create_ed25519_keypair(
        private_key_path: str = "logs/device_ed25519_key.pem",
        public_key_path: str = "logs/device_ed25519_pub.pem"
    ) -> Tuple[str, str, str]:
        """
        Loads existing Ed25519 public key or generates a new keypair in OS KeystoreManager.
        Returns: ("[KEYSTORE_MANAGED]", public_key_pem, fingerprint)
        """
        pub_pem = keystore_manager.get_or_create_device_keypair()
        fingerprint = CryptoUtils.compute_key_fingerprint(pub_pem)

        log_structured(
            backend_log,
            "INFO",
            f"[CryptoUtils] Managed Ed25519 device keypair via KeystoreManager. Fingerprint: {fingerprint}"
        )
        return "[KEYSTORE_MANAGED]", pub_pem, fingerprint

    @staticmethod
    def compute_key_fingerprint(public_key_pem: str) -> str:
        """
        Computes SHA-256 fingerprint for a public key string.
        """
        digest = hashlib.sha256(public_key_pem.strip().encode("utf-8")).hexdigest()
        return f"SHA256:{digest[:16]}:{digest[16:32]}"

    @staticmethod
    def sign_message_ed25519(private_key_pem: str, message: bytes) -> bytes:
        """
        Signs message bytes using Ed25519 private key stored in OS KeystoreManager.
        """
        return keystore_manager.sign_data(message)

    @staticmethod
    def verify_signature_ed25519(public_key_pem: str, signature: bytes, message: bytes) -> bool:
        """
        Verifies Ed25519 signature for a given message.
        """
        return keystore_manager.verify_signature(public_key_pem, signature, message)

    @staticmethod
    def hash_password_pbkdf2(password: str, salt: bytes = None) -> Tuple[str, str]:
        """
        Hashes password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
        Returns: (hash_hex, salt_hex)
        """
        if salt is None:
            salt = secrets.token_bytes(16)

        derived = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-8"),
            salt=salt,
            iterations=100000
        )
        return derived.hex(), salt.hex()

    @staticmethod
    def verify_password_pbkdf2(password: str, stored_hash_hex: str, stored_salt_hex: str) -> bool:
        """
        Verifies password against stored PBKDF2 hash and salt.
        """
        salt = bytes.fromhex(stored_salt_hex)
        computed_hash_hex, _ = CryptoUtils.hash_password_pbkdf2(password, salt)
        return secrets.compare_digest(computed_hash_hex, stored_hash_hex)

    @staticmethod
    def generate_secure_token(length_or_prefix: Any = 32) -> str:
        """
        Generates a cryptographically secure random urlsafe token with optional prefix.
        """
        if isinstance(length_or_prefix, str):
            tok = secrets.token_urlsafe(32)
            return f"{length_or_prefix}_{tok}"
        length = length_or_prefix if isinstance(length_or_prefix, int) else 32
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_uuid(prefix: str = "") -> str:
        """
        Generates a random UUID4 string with optional prefix.
        """
        uid = str(uuid.uuid4())
        return f"{prefix}_{uid}" if prefix else uid


crypto_utils = CryptoUtils()
