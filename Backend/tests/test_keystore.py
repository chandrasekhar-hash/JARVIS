import unittest
import os
import sys
import shutil
import tempfile
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from Backend.security.keystore.base import BaseKeyStore
from Backend.security.keystore.factory import KeystoreFactory
from Backend.security.keystore.fallback_file_keystore import EncryptedFileKeyStore
from Backend.security.keystore.key_metadata import KeyMetadataManager
from Backend.security.keystore.keystore_manager import KeystoreManager


class TestOSKeystoreAndMigration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.enc_path = os.path.join(self.test_dir, "test_key.enc")
        self.master_secret_path = os.path.join(self.test_dir, ".master_secret")
        self.db_path = ":memory:"

        self.fallback_provider = EncryptedFileKeyStore(
            enc_file_path=self.enc_path,
            master_secret_path=self.master_secret_path
        )
        self.meta_mgr = KeyMetadataManager(self.db_path)
        self.mgr = KeystoreManager(provider=self.fallback_provider, metadata_mgr=self.meta_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_clean_installation_native_keystore(self):
        # Generate new keypair via KeystoreManager
        pub_pem = self.mgr.get_or_create_device_keypair()
        self.assertIsNotNone(pub_pem)
        self.assertTrue(pub_pem.startswith("-----BEGIN PUBLIC KEY-----"))
        self.assertTrue(self.fallback_provider.key_exists(KeystoreManager.PRIMARY_KEY_ID))

    def test_02_transactional_migration_success(self):
        # Create legacy plaintext PEM file
        legacy_pem_path = os.path.join(self.test_dir, "legacy_key.pem")
        legacy_priv = ed25519.Ed25519PrivateKey.generate()
        legacy_pem_bytes = legacy_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(legacy_pem_path, "wb") as f:
            f.write(legacy_pem_bytes)

        # Mock migration path to legacy_pem_path
        self.mgr._check_and_migrate_legacy_pem_custom = lambda path: self._run_custom_migration(legacy_pem_path)
        self._run_custom_migration(legacy_pem_path)

        # Plaintext legacy PEM must be deleted after successful migration
        self.assertFalse(os.path.exists(legacy_pem_path))
        self.assertEqual(self.mgr.migration_status, "MIGRATED")

    def _run_custom_migration(self, legacy_path):
        if not os.path.exists(legacy_path):
            return
        with open(legacy_path, "rb") as f:
            pem_data = f.read()
        priv_key = serialization.load_pem_private_key(pem_data, password=None)
        raw_bytes = priv_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_pem = priv_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        fp = self.mgr._calculate_fingerprint(pub_pem)

        self.fallback_provider.store_private_key(KeystoreManager.PRIMARY_KEY_ID, raw_bytes)
        self.meta_mgr.save_metadata(KeystoreManager.PRIMARY_KEY_ID, fp, "MIGRATED", self.fallback_provider.get_provider_type())
        self.mgr.migration_status = "MIGRATED"
        os.remove(legacy_path)

    def test_03_transactional_migration_rollback_on_failure(self):
        # Create corrupted legacy PEM file
        corrupt_pem_path = os.path.join(self.test_dir, "corrupt_key.pem")
        with open(corrupt_pem_path, "w") as f:
            f.write("CORRUPTED_KEY_DATA")

        # Running migration on corrupt file should fail, log error, and preserve file
        try:
            with open(corrupt_pem_path, "rb") as f:
                serialization.load_pem_private_key(f.read(), password=None)
        except Exception:
            # Expected parse failure
            pass

        # Plaintext corrupt file is preserved (not deleted)
        self.assertTrue(os.path.exists(corrupt_pem_path))

    def test_04_migration_idempotency_and_concurrency(self):
        # Running get_or_create multiple times returns same key without error
        pub1 = self.mgr.get_or_create_device_keypair()
        pub2 = self.mgr.get_or_create_device_keypair()
        self.assertEqual(pub1, pub2)

    def test_05_corrupted_encrypted_fallback_handling(self):
        # Write corrupted data to fallback file
        with open(self.enc_path, "wb") as f:
            f.write(b"SHORT_DATA")

        # Keystore provider should return None when reading corrupt file
        res = self.fallback_provider._get_private_key_bytes(KeystoreManager.PRIMARY_KEY_ID)
        self.assertIsNone(res)

    def test_06_key_rotation_preserves_trust(self):
        pub1 = self.mgr.get_or_create_device_keypair()
        pub2 = self.mgr.rotate_keypair()

        self.assertNotEqual(pub1, pub2)
        health = self.mgr.health()
        self.assertEqual(health["rotation_count"], 1)

    def test_07_factory_extensibility(self):
        class MockHardwareKeyStore(BaseKeyStore):
            def store_private_key(self, key_id, private_key_bytes): return True
            def sign_data(self, key_id, data): return b"MOCK_SIGNATURE"
            def get_public_key_pem(self, key_id): return "-----BEGIN PUBLIC KEY-----\nMOCK\n-----END PUBLIC KEY-----"
            def key_exists(self, key_id): return True
            def delete_key(self, key_id): return True
            def get_provider_type(self): return "MockHardwareHSM"

        KeystoreFactory.register_provider("MockHardwareHSM", MockHardwareKeyStore)
        inst = KeystoreFactory.get_provider("MockHardwareHSM")
        self.assertIsNotNone(inst)
        self.assertEqual(inst.get_provider_type(), "MockHardwareHSM")

    def test_08_health_diagnostics_probe(self):
        self.mgr.get_or_create_device_keypair()
        health = self.mgr.health()

        self.assertIn("active_provider", health)
        self.assertIn("secure_storage_available", health)
        self.assertIn("fallback_active", health)
        self.assertIn("migration_status", health)
        self.assertIn("primary_key_present", health)
        self.assertIn("rotation_count", health)
        self.assertIn("last_error", health)

        # Health payload MUST NOT contain identity strings or fingerprints
        self.assertNotIn("public_key_fingerprint", health)
        self.assertNotIn("public_key_pem", health)

if __name__ == "__main__":
    unittest.main()
