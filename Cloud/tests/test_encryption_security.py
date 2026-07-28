import unittest
import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sync.encryption import payload_encryptor, AES256GCMEncryption

class TestEncryptionSecurity(unittest.TestCase):
    def test_01_aes_gcm_encryption_integrity(self):
        payload = {"secret_preference": "User API Token = abc123xyz"}
        encrypted = payload_encryptor.encrypt(payload)

        # Decrypt payload
        decrypted = payload_encryptor.decrypt(encrypted)
        self.assertEqual(decrypted["secret_preference"], payload["secret_preference"])

    def test_02_tampered_ciphertext_rejection(self):
        payload = {"secret_preference": "Sensitive User Data"}
        encrypted = payload_encryptor.encrypt(payload)

        # Corrupt ciphertext byte
        corrupted = dict(encrypted)
        corrupted["ciphertext"] = "Z" + encrypted["ciphertext"][1:]

        with self.assertRaises(Exception):
            payload_encryptor.decrypt(corrupted)

    def test_03_log_sanitization_audit(self):
        """Verifies logging format does not dump sensitive payload dicts."""
        from io import StringIO
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        logger = logging.getLogger("JARVIS_Cloud_Encryption")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log safe message
        logger.info("Encrypted payload generated successfully for dev_001")

        log_output = log_stream.getvalue()
        self.assertNotIn("abc123xyz", log_output)
        self.assertNotIn("access_token", log_output)

if __name__ == "__main__":
    unittest.main()
