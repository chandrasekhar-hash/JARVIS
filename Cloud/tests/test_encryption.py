import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sync.encryption import payload_encryptor, AES256GCMEncryption

class TestEncryptionEngine(unittest.TestCase):
    def test_01_encrypt_and_decrypt_payload(self):
        payload = {
            "user_id": "usr_crypto_1",
            "memory_fact": "User prefers Groq Llama-3.3-70B model",
            "timestamp": 123456789.0
        }

        encrypted = payload_encryptor.encrypt(payload, compress_threshold=10000)
        self.assertIn("nonce", encrypted)
        self.assertIn("ciphertext", encrypted)
        self.assertIn("tag", encrypted)
        self.assertFalse(encrypted["compressed"])

        decrypted = payload_encryptor.decrypt(encrypted)
        self.assertEqual(decrypted["user_id"], payload["user_id"])
        self.assertEqual(decrypted["memory_fact"], payload["memory_fact"])

    def test_02_tag_verification(self):
        payload = {"data": "secret_info"}
        encrypted = payload_encryptor.encrypt(payload)

        is_valid = payload_encryptor.verify_tag(encrypted["nonce"], encrypted["ciphertext"], encrypted["tag"])
        self.assertTrue(is_valid)

        # Tampered ciphertext tag verification must fail
        tampered_ciphertext = "A" + encrypted["ciphertext"][1:]
        is_tampered_valid = payload_encryptor.verify_tag(encrypted["nonce"], tampered_ciphertext, encrypted["tag"])
        self.assertFalse(is_tampered_valid)

if __name__ == "__main__":
    unittest.main()
