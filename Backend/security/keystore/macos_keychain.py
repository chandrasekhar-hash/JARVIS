import subprocess
import logging
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from Backend.security.keystore.base import BaseKeyStore
from Backend.security.keystore.factory import KeystoreFactory

logger = logging.getLogger("JARVIS_MacOSKeyStore")


class MacOSKeyStore(BaseKeyStore):
    """
    Apple Keychain KeyStore Provider for macOS.
    Stores Ed25519 private key bytes securely in user's Apple Keychain.
    """

    SERVICE_NAME = "jarvis_ed25519_identity"

    def get_provider_type(self) -> str:
        return "MacOSKeychain"

    def store_private_key(self, key_id: str, private_key_bytes: bytes) -> bool:
        try:
            import keyring
            keyring.set_password(self.SERVICE_NAME, key_id, private_key_bytes.hex())
            logger.info(f"Successfully stored key '{key_id}' in macOS Keychain via keyring")
            return True
        except Exception as e:
            logger.warning(f"Keyring store failed ({e}). Falling back to security CLI...")

        # CLI Fallback (/usr/bin/security)
        try:
            hex_str = private_key_bytes.hex()
            cmd = [
                "/usr/bin/security", "add-generic-password",
                "-a", key_id,
                "-s", self.SERVICE_NAME,
                "-w", hex_str,
                "-U"  # Update if exists
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                logger.info(f"Successfully stored key '{key_id}' in macOS Keychain via security CLI")
                return True
            else:
                logger.error(f"security CLI add-generic-password failed: {res.stderr}")
        except Exception as ex:
            logger.error(f"MacOSKeyStore store_private_key error: {ex}")
        return False

    def _get_private_key_bytes(self, key_id: str) -> Optional[bytes]:
        try:
            import keyring
            val = keyring.get_password(self.SERVICE_NAME, key_id)
            if val:
                return bytes.fromhex(val)
        except Exception:
            pass

        # CLI Fallback (/usr/bin/security)
        try:
            cmd = [
                "/usr/bin/security", "find-generic-password",
                "-a", key_id,
                "-s", self.SERVICE_NAME,
                "-w"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return bytes.fromhex(res.stdout.strip())
        except Exception as ex:
            logger.error(f"MacOSKeyStore _get_private_key_bytes error: {ex}")
        return None

    def key_exists(self, key_id: str) -> bool:
        return self._get_private_key_bytes(key_id) is not None

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        raw_bytes = self._get_private_key_bytes(key_id)
        if not raw_bytes:
            raise KeyError(f"Key '{key_id}' not found in macOS Keychain.")
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
            logger.info(f"Deleted key '{key_id}' from macOS Keychain via keyring")
            return True
        except Exception:
            pass

        try:
            cmd = [
                "/usr/bin/security", "delete-generic-password",
                "-a", key_id,
                "-s", self.SERVICE_NAME
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return res.returncode == 0
        except Exception:
            return False


KeystoreFactory.register_provider("MacOSKeychain", MacOSKeyStore)
