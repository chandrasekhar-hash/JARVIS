import logging
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from Backend.security.keystore.base import BaseKeyStore
from Backend.security.keystore.factory import KeystoreFactory

logger = logging.getLogger("JARVIS_WindowsDPAPIKeyStore")


class WindowsDPAPIKeyStore(BaseKeyStore):
    """
    Windows DPAPI KeyStore Provider for Windows.
    Stores Ed25519 private key bytes securely using Windows Data Protection API (DPAPI) via keyring / win32crypt.
    """

    SERVICE_NAME = "jarvis_ed25519_identity"

    def get_provider_type(self) -> str:
        return "WindowsDPAPI"

    def store_private_key(self, key_id: str, private_key_bytes: bytes) -> bool:
        try:
            import keyring
            keyring.set_password(self.SERVICE_NAME, key_id, private_key_bytes.hex())
            logger.info(f"Successfully stored key '{key_id}' in Windows DPAPI via keyring")
            return True
        except Exception as e:
            logger.error(f"WindowsDPAPIKeyStore store_private_key failed: {e}")
            return False

    def _get_private_key_bytes(self, key_id: str) -> Optional[bytes]:
        try:
            import keyring
            val = keyring.get_password(self.SERVICE_NAME, key_id)
            if val:
                return bytes.fromhex(val)
        except Exception as e:
            logger.error(f"WindowsDPAPIKeyStore _get_private_key_bytes failed: {e}")
        return None

    def key_exists(self, key_id: str) -> bool:
        return self._get_private_key_bytes(key_id) is not None

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        raw_bytes = self._get_private_key_bytes(key_id)
        if not raw_bytes:
            raise KeyError(f"Key '{key_id}' not found in Windows DPAPI.")
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
        try:
            import keyring
            keyring.delete_password(self.SERVICE_NAME, key_id)
            logger.info(f"Deleted key '{key_id}' from Windows DPAPI via keyring")
            return True
        except Exception:
            return False


KeystoreFactory.register_provider("WindowsDPAPI", WindowsDPAPIKeyStore)
