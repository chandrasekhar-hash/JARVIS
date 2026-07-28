import os
import json
import zlib
import secrets
import base64
import logging
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config.settings import cloud_settings

logger = logging.getLogger("JARVIS_Cloud_Encryption")

COMPRESSION_THRESHOLD_BYTES = int(os.getenv("SYNC_COMPRESSION_THRESHOLD_BYTES", "1024"))


class AES256GCMEncryption:
    """
    AES-256-GCM Application-Layer Payload Encryption over WSS Transport.
    Supports configurable threshold compression (>1 KB compressed with zlib before encryption).
    """

    def __init__(self, key_bytes: bytes = None):
        if key_bytes:
            self.key = key_bytes
        else:
            # Derive 32-byte key from jwt_secret for application-layer encryption
            raw = cloud_settings.jwt_secret.encode("utf-8")
            self.key = (raw * (32 // len(raw) + 1))[:32]
        self.aesgcm = AESGCM(self.key)

    def generate_nonce(self) -> bytes:
        return secrets.token_bytes(12)  # 96-bit standard AES-GCM nonce

    def encrypt(self, payload: Dict[str, Any], compress_threshold: int = COMPRESSION_THRESHOLD_BYTES) -> Dict[str, Any]:
        """
        Compresses payload if >= compress_threshold and encrypts using AES-256-GCM.
        Returns format: {"nonce": "...", "ciphertext": "...", "tag": "...", "compressed": bool}
        """
        payload_bytes = json.dumps(payload).encode("utf-8")
        compressed = False

        if len(payload_bytes) >= compress_threshold:
            payload_bytes = zlib.compress(payload_bytes)
            compressed = True

        nonce = self.generate_nonce()
        # AESGCM.encrypt returns ciphertext + 16-byte authentication tag appended
        ciphertext_and_tag = self.aesgcm.encrypt(nonce, payload_bytes, associated_data=None)

        ciphertext = ciphertext_and_tag[:-16]
        tag = ciphertext_and_tag[-16:]

        return {
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "tag": base64.b64encode(tag).decode("utf-8"),
            "compressed": compressed
        }

    def decrypt(self, encrypted_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypts AES-256-GCM encrypted payload and decompresses if compressed flag is set.
        """
        nonce = base64.b64decode(encrypted_payload["nonce"])
        ciphertext = base64.b64decode(encrypted_payload["ciphertext"])
        tag = base64.b64decode(encrypted_payload["tag"])
        compressed = encrypted_payload.get("compressed", False)

        ciphertext_and_tag = ciphertext + tag
        decrypted_bytes = self.aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data=None)

        if compressed:
            decrypted_bytes = zlib.decompress(decrypted_bytes)

        return json.loads(decrypted_bytes.decode("utf-8"))

    def verify_tag(self, nonce_b64: str, ciphertext_b64: str, tag_b64: str) -> bool:
        try:
            nonce = base64.b64decode(nonce_b64)
            ciphertext = base64.b64decode(ciphertext_b64)
            tag = base64.b64decode(tag_b64)
            self.aesgcm.decrypt(nonce, ciphertext + tag, associated_data=None)
            return True
        except Exception:
            return False

    def rotate_key(self, new_key_bytes: bytes):
        if len(new_key_bytes) != 32:
            raise ValueError("AES-256 key must be exactly 32 bytes.")
        self.key = new_key_bytes
        self.aesgcm = AESGCM(self.key)


payload_encryptor = AES256GCMEncryption()
