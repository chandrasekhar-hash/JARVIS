import unittest
import os
import json
from fastapi.testclient import TestClient

from identity.crypto_utils import crypto_utils
from identity.identity_manager import identity_manager
from identity.session_manager import session_manager
from identity.identity_models import DeviceTrustState, SessionStatus
from main import app

class TestIdentityAndSecurityLayer(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.user, self.device = identity_manager.initialize()
        identity_manager.update_device_trust_state(DeviceTrustState.TRUSTED)

    def test_01_ed25519_crypto_utils(self):
        priv_pem, pub_pem, fingerprint = crypto_utils.get_or_create_ed25519_keypair()
        self.assertTrue(pub_pem.startswith("-----BEGIN PUBLIC KEY-----"))
        self.assertTrue(fingerprint.startswith("SHA256:"))

        # Sign & verify test message
        msg = b"JARVIS Ed25519 Security Verification Signature"
        sig = crypto_utils.sign_message_ed25519(priv_pem, msg)
        valid = crypto_utils.verify_signature_ed25519(pub_pem, sig, msg)
        self.assertTrue(valid)

        # Tampered message must fail verification
        tampered_msg = b"Tampered Message"
        self.assertFalse(crypto_utils.verify_signature_ed25519(pub_pem, sig, tampered_msg))

    def test_02_local_identity_and_device_provisioning(self):
        self.assertIsNotNone(self.user.user_id)
        self.assertTrue(len(self.user.display_name) > 0)

        self.assertIsNotNone(self.device.device_id)
        self.assertEqual(self.device.trust_state, DeviceTrustState.TRUSTED)
        self.assertTrue(self.device.public_key_fingerprint.startswith("SHA256:"))

    def test_03_device_trust_state_transitions(self):
        # Update to REVOKED
        revoked = identity_manager.update_device_trust_state(DeviceTrustState.REVOKED)
        self.assertEqual(revoked.trust_state, DeviceTrustState.REVOKED)

        # Restore to TRUSTED
        trusted = identity_manager.update_device_trust_state(DeviceTrustState.TRUSTED)
        self.assertEqual(trusted.trust_state, DeviceTrustState.TRUSTED)

    def test_04_session_lifecycle(self):
        token_pair, session = session_manager.issue_session(self.user.user_id, self.device.device_id)
        self.assertIsNotNone(token_pair.access_token)
        self.assertIsNotNone(token_pair.refresh_token)

        # Validate access token
        valid, sess_obj, err = session_manager.validate_access_token(token_pair.access_token)
        self.assertTrue(valid)
        self.assertEqual(sess_obj.session_id, session.session_id)

        # Refresh session
        ref_ok, new_pair, ref_err = session_manager.refresh_session(token_pair.refresh_token)
        self.assertTrue(ref_ok)
        self.assertIsNotNone(new_pair.access_token)

        # Revoke session
        rev_ok = session_manager.revoke_session(session.session_id)
        self.assertTrue(rev_ok)

        # Validate revoked session fails
        val_after_rev, _, _ = session_manager.validate_access_token(new_pair.access_token)
        self.assertFalse(val_after_rev)

    def test_05_rest_api_endpoints(self):
        # 1. GET /api/identity
        r1 = self.client.get("/api/identity")
        self.assertEqual(r1.status_code, 200)
        self.assertIn("user_profile", r1.json())

        # 2. PUT /api/identity
        r2 = self.client.put("/api/identity", json={"display_name": "Tony Stark", "email": "stark@jarvis.ai"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["user_profile"]["display_name"], "Tony Stark")

        # 3. GET /api/device
        r3 = self.client.get("/api/device")
        self.assertEqual(r3.status_code, 200)
        self.assertIn("device_profile", r3.json())

        # 4. PUT /api/device/trust
        r4 = self.client.put("/api/device/trust", json={"trust_state": "trusted"})
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()["device_profile"]["trust_state"], "trusted")

        # 5. GET /api/security/status
        r5 = self.client.get("/api/security/status")
        self.assertEqual(r5.status_code, 200)
        self.assertTrue(r5.json()["security_status"]["local_first_mode"])
        self.assertEqual(r5.json()["security_status"]["crypto_algorithm"], "Ed25519")

        # 6. POST /api/session/issue
        r6 = self.client.post("/api/session/issue")
        self.assertEqual(r6.status_code, 200)
        sess_data = r6.json()
        self.assertIn("token_pair", sess_data)

        # 7. POST /api/session/refresh
        r7 = self.client.post("/api/session/refresh", json={"refresh_token": sess_data["token_pair"]["refresh_token"]})
        self.assertEqual(r7.status_code, 200)

        # 8. POST /api/session/logout
        r8 = self.client.post("/api/session/logout", json={"session_id": sess_data["session"]["session_id"]})
        self.assertEqual(r8.status_code, 200)


if __name__ == "__main__":
    unittest.main()
