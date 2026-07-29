import os
import hashlib
import logging
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from .base import BaseKeyStore
from .factory import KeystoreFactory
from .key_metadata import key_metadata_manager, KeyMetadataManager

# Ensure providers are loaded into factory
import security.keystore.macos_keychain
import security.keystore.windows_dpapi
import security.keystore.linux_secret_service
import security.keystore.fallback_file_keystore

logger = logging.getLogger("JARVIS_KeystoreManager")


class KeystoreManager:
    """
    Unified KeystoreManager entrypoint for J.A.R.V.I.S. Identity Security.
    Manages key generation, loading, signature creation, key rotation,
    health diagnostics, and 7-step transactional legacy migration.
    """

    PRIMARY_KEY_ID = "device_ed25519_primary"

    def __init__(self, provider: Optional[BaseKeyStore] = None, metadata_mgr: Optional[KeyMetadataManager] = None):
        self.provider = provider or KeystoreFactory.get_preferred_provider()
        self.metadata_mgr = metadata_mgr or key_metadata_manager
        self.last_error: Optional[str] = None
        self.migration_status: str = "NATIVE_KEYSTORE"

        # Execute automatic legacy migration on startup
        self._check_and_migrate_legacy_pem()

    def _calculate_fingerprint(self, pub_pem: str) -> str:
        return "sha256:" + hashlib.sha256(pub_pem.encode("utf-8")).hexdigest()

    def _check_and_migrate_legacy_pem(self):
        """
        Transactional 7-Step Legacy Migration:
        1. Detect legacy PEM (logs/device_ed25519_key.pem)
        2. Read legacy private key
        3. Import into OS Keystore
        4. Verify signing capability
        5. Verify public key fingerprint
        6. Mark migration success in SQLite metadata
        7. Securely delete plaintext PEM
        Rolls back automatically if any verification step fails.
        """
        log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../logs"))
        legacy_pem_path = os.path.join(log_dir, "device_ed25519_key.pem")

        if not os.path.exists(legacy_pem_path):
            return

        logger.info(f"Detected legacy plaintext key file at '{legacy_pem_path}'. Initiating 7-step transactional migration...")

        try:
            # Step 1 & 2: Read legacy key
            with open(legacy_pem_path, "rb") as f:
                pem_data = f.read()

            legacy_priv_key = serialization.load_pem_private_key(pem_data, password=None)
            if not isinstance(legacy_priv_key, ed25519.Ed25519PrivateKey):
                raise ValueError("Legacy key is not a valid Ed25519 private key.")

            raw_bytes = legacy_priv_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            legacy_pub_pem = legacy_priv_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode("utf-8")
            expected_fp = self._calculate_fingerprint(legacy_pub_pem)

            # Step 3: Import into OS Keystore
            success = self.provider.store_private_key(self.PRIMARY_KEY_ID, raw_bytes)
            if not success:
                raise RuntimeError("Failed to store private key in OS keystore provider.")

            # Step 4: Verify signing capability
            test_challenge = b"JARVIS_MIGRATION_VERIFY_CHALLENGE"
            sig = self.provider.sign_data(self.PRIMARY_KEY_ID, test_challenge)
            legacy_priv_key.public_key().verify(sig, test_challenge)

            # Step 5: Verify public key fingerprint
            imported_pub_pem = self.provider.get_public_key_pem(self.PRIMARY_KEY_ID)
            if not imported_pub_pem:
                raise RuntimeError("Failed to retrieve imported public key PEM.")
            imported_fp = self._calculate_fingerprint(imported_pub_pem)

            if imported_fp != expected_fp:
                raise ValueError(f"Fingerprint mismatch! Expected {expected_fp}, got {imported_fp}")

            # Step 6: Mark migration success in SQLite metadata
            self.metadata_mgr.save_metadata(
                key_id=self.PRIMARY_KEY_ID,
                fingerprint=imported_fp,
                migration_status="MIGRATED",
                provider_type=self.provider.get_provider_type()
            )
            self.migration_status = "MIGRATED"

            # Step 7: Securely delete plaintext PEM
            os.remove(legacy_pem_path)
            logger.info("TRANSACTIONAL MIGRATION SUCCESSFUL! Plaintext legacy PEM safely deleted.")

        except Exception as e:
            self.last_error = f"Migration failed: {e}"
            logger.error(f"TRANSACTIONAL MIGRATION FAILED ({e}). Rolling back and preserving legacy PEM file intact!")
            # Rollback: remove imported key if stored
            try:
                self.provider.delete_key(self.PRIMARY_KEY_ID)
            except Exception:
                pass

    def get_or_create_device_keypair(self) -> str:
        """
        Returns public key PEM string for primary device keypair.
        Generates a new keypair in Keystore if non-existent.
        """
        if not self.provider.key_exists(self.PRIMARY_KEY_ID):
            logger.info("No primary key found in Keystore. Generating new Ed25519 keypair...")
            priv_key = ed25519.Ed25519PrivateKey.generate()
            raw_bytes = priv_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            self.provider.store_private_key(self.PRIMARY_KEY_ID, raw_bytes)
            pub_pem = self.provider.get_public_key_pem(self.PRIMARY_KEY_ID)
            fp = self._calculate_fingerprint(pub_pem)

            self.metadata_mgr.save_metadata(
                key_id=self.PRIMARY_KEY_ID,
                fingerprint=fp,
                migration_status="NATIVE_KEYSTORE",
                provider_type=self.provider.get_provider_type()
            )

        pub_pem = self.provider.get_public_key_pem(self.PRIMARY_KEY_ID)
        if not pub_pem:
            raise RuntimeError("Failed to retrieve public key from Keystore.")
        return pub_pem

    def sign_data(self, data: bytes, key_id: str = PRIMARY_KEY_ID) -> bytes:
        return self.provider.sign_data(key_id, data)

    def verify_signature(self, pub_pem: str, signature: bytes, data: bytes) -> bool:
        try:
            pub_key = serialization.load_pem_public_key(pub_pem.encode("utf-8"))
            if isinstance(pub_key, ed25519.Ed25519PublicKey):
                pub_key.verify(signature, data)
                return True
        except Exception:
            pass
        return False

    def export_public_key_pem(self, key_id: str = PRIMARY_KEY_ID) -> Optional[str]:
        return self.provider.get_public_key_pem(key_id)

    def rotate_keypair(self, key_id: str = PRIMARY_KEY_ID) -> str:
        """
        Rotates keypair, updates metadata, and returns new public key PEM string.
        """
        logger.info(f"Rotating keypair for '{key_id}'...")
        new_priv_key = ed25519.Ed25519PrivateKey.generate()
        raw_bytes = new_priv_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.provider.store_private_key(key_id, raw_bytes)
        pub_pem = self.provider.get_public_key_pem(key_id)
        fp = self._calculate_fingerprint(pub_pem)

        meta = self.metadata_mgr.get_metadata(key_id)
        rot_count = (meta["rotation_count"] + 1) if meta else 1

        self.metadata_mgr.save_metadata(
            key_id=key_id,
            fingerprint=fp,
            migration_status=meta.get("migration_status", "NATIVE_KEYSTORE") if meta else "NATIVE_KEYSTORE",
            provider_type=self.provider.get_provider_type(),
            rotation_count=rot_count
        )
        return pub_pem

    def health(self) -> Dict[str, Any]:
        meta = self.metadata_mgr.get_metadata(self.PRIMARY_KEY_ID)
        return {
            "active_provider": self.provider.get_provider_type(),
            "secure_storage_available": self.provider.get_provider_type() != "EncryptedFileFallback",
            "fallback_active": self.provider.get_provider_type() == "EncryptedFileFallback",
            "migration_status": self.migration_status,
            "primary_key_present": self.provider.key_exists(self.PRIMARY_KEY_ID),
            "rotation_count": meta["rotation_count"] if meta else 0,
            "last_error": self.last_error
        }


keystore_manager = KeystoreManager()
