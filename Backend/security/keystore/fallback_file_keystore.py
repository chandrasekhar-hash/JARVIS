import os
import logging
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from .base import BaseKeyStore
from .factory import KeystoreFactory

logger = logging.getLogger("JARVIS_EncryptedFileKeyStore")


class EncryptedFileKeyStore(BaseKeyStore):
    """
    AES-256-GCM Encrypted File KeyStore Fallback Provider.
    Used when native OS keystores (Keychain, DPAPI, SecretService) are unavailable.
    Protects private keys using AES-256-GCM authenticated encryption and random master secret.
    """

    def __init__(self, enc_file_path: Optional[str] = None, master_secret_path: Optional[str] = None):
        log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../logs"))
        os.makedirs(log_dir, exist_ok=True)
        self.enc_file_path = enc_file_path or os.path.join(log_dir, "device_ed25519_key.enc")
        self.master_secret_path = master_secret_path or os.path.join(log_dir, ".master_secret")

    def get_provider_type(self) -> str:
        return "EncryptedFileFallback"

    def _get_or_create_master_secret(self) -> bytes:
        if os.path.exists(self.master_secret_path):
            with open(self.master_secret_path, "rb") as f:
                return f.read()
        else:
            secret = os.urandom(32)
            # Save master secret with strict 0600 permissions
            with open(self.master_secret_path, "wb") as f:
                f.write(secret)
            try:
                os.chmod(self.master_secret_path, 0o600)
            except Exception:
                pass
            logger.warning("Native OS keystore unavailable. Created random 256-bit master secret for AES-256-GCM fallback encryption.")
            return secret

    def _derive_aes_key(self, salt: bytes) -> bytes:
        master_secret = self._get_or_create_master_secret()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        return kdf.derive(master_secret)

    def store_private_key(self, key_id: str, private_key_bytes: bytes) -> bool:
        try:
            salt = os.urandom(16)
            aes_key = self._derive_aes_key(salt)
            aesgcm = AESGCM(aes_key)
            iv = os.urandom(12)

            ciphertext = aesgcm.encrypt(iv, private_key_bytes, key_id.encode("utf-8"))

            # Format: [16-byte Salt][12-byte IV][Ciphertext]
            with open(self.enc_file_path, "wb") as f:
                f.write(salt + iv + ciphertext)
            try:
                os.chmod(self.enc_file_path, 0o600)
            except Exception:
                pass

            logger.warning(f"Stored encrypted private key '{key_id}' at '{self.enc_file_path}' (AES-256-GCM fallback)")
            return True
        except Exception as e:
            logger.error(f"EncryptedFileKeyStore store_private_key failed: {e}")
            return False

    def _get_private_key_bytes(self, key_id: str) -> Optional[bytes]:
        if not os.path.exists(self.enc_file_path):
            return None
        try:
            with open(self.enc_file_path, "rb") as f:
                raw = f.read()
            if len(raw) < 28:
                logger.error("Corrupted fallback key file (file size too small).")
                return None

            salt = raw[:16]
            iv = raw[16:28]
            ciphertext = raw[28:]

            aes_key = self._derive_aes_key(salt)
            aesgcm = AESGCM(aes_key)
            return aesgcm.decrypt(iv, ciphertext, key_id.encode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to decrypt fallback private key file: {e}")
            return None

    def key_exists(self, key_id: str) -> bool:
        return self._get_private_key_bytes(key_id) is not None

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        raw_bytes = self._get_private_key_bytes(key_id)
        if not raw_bytes:
            raise KeyError(f"Key '{key_id}' not found in fallback encrypted file.")
        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
        return priv_key.sign(data)

    def get_public_key_pem(self, key_id: str) -> Optional[str]:
        raw_bytes = self._get_private_key_bytes(key_id)
        if not raw_bytes:
            return None
        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
        pub_bytes = priv_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pub_bytes.decode("utf-8")

    def delete_key(self, key_id: str) -> bool:
        if os.path.exists(self.enc_file_path):
            try:
                os.remove(self.enc_file_path)
                logger.info(f"Deleted encrypted fallback key file '{self.enc_file_path}'")
                return True
            except Exception:
                return False
        return True


KeystoreFactory.register_provider("EncryptedFileFallback", EncryptedFileKeyStore)
