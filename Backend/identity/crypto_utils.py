import os
import secrets
import uuid
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from tools.telemetry import log_structured, backend_log

ED25519_KEY_PATH = "logs/device_ed25519_key.pem"
ED25519_PUB_PATH = "logs/device_ed25519_pub.pem"

class CryptoUtils:
    """
    Provides modern cryptography services: Ed25519 key generation & signing,
    SHA-256 fingerprinting, PBKDF2 password hashing with salt, and secure token generation.
    """

    @staticmethod
    def get_or_create_ed25519_keypair(
        private_key_path: str = ED25519_KEY_PATH,
        public_key_path: str = ED25519_PUB_PATH
    ) -> Tuple[str, str, str]:
        """
        Loads existing Ed25519 keypair or generates a new one.
        Returns: (private_key_pem, public_key_pem, fingerprint)
        """
        os.makedirs(os.path.dirname(private_key_path), exist_ok=True)

        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            with open(private_key_path, "rb") as f:
                priv_pem = f.read().decode("utf-8")
            with open(public_key_path, "rb") as f:
                pub_pem = f.read().decode("utf-8")
            fingerprint = CryptoUtils.compute_key_fingerprint(pub_pem)
            return priv_pem, pub_pem, fingerprint

        # Generate new Ed25519 keypair
        priv_key = ed25519.Ed25519PrivateKey.generate()
        pub_key = priv_key.public_key()

        priv_bytes = priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        pub_bytes = pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        priv_pem = priv_bytes.decode("utf-8")
        pub_pem = pub_bytes.decode("utf-8")
        fingerprint = CryptoUtils.compute_key_fingerprint(pub_pem)

        with open(private_key_path, "wb") as f:
            f.write(priv_bytes)
        with open(public_key_path, "wb") as f:
            f.write(pub_bytes)

        log_structured(
            backend_log,
            "INFO",
            f"[CryptoUtils] Generated new Ed25519 device keypair. Fingerprint: {fingerprint}"
        )
        return priv_pem, pub_pem, fingerprint

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
        Signs message bytes using Ed25519 private key.
        """
        priv_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None
        )
        return priv_key.sign(message)

    @staticmethod
    def verify_signature_ed25519(public_key_pem: str, signature: bytes, message: bytes) -> bool:
        """
        Verifies Ed25519 signature for a given message.
        """
        try:
            pub_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            pub_key.verify(signature, message)
            return True
        except Exception:
            return False

    @staticmethod
    def generate_secure_token(prefix: str = "jarvis_tok") -> str:
        """
        Generates a cryptographically secure random token string.
        """
        random_bytes = secrets.token_urlsafe(32)
        return f"{prefix}_{random_bytes}"

    @staticmethod
    def generate_uuid(prefix: str = "id") -> str:
        """
        Generates a secure UUID v4 string with optional prefix.
        """
        return f"{prefix}_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def hash_password_pbkdf2(password: str, salt: bytes = None) -> Tuple[str, str]:
        """
        Hashes password using PBKDF2 with SHA-256 and unique salt.
        Returns: (hash_hex, salt_hex)
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return key.hex(), salt.hex()

    @staticmethod
    def verify_password_pbkdf2(password: str, hash_hex: str, salt_hex: str) -> bool:
        """
        Verifies plaintext password against PBKDF2 hash_hex and salt_hex.
        """
        salt = bytes.fromhex(salt_hex)
        calc_hash, _ = CryptoUtils.hash_password_pbkdf2(password, salt)
        return secrets.compare_digest(calc_hash, hash_hex)

crypto_utils = CryptoUtils()
