import unittest
import base64
import os
import sys

# Ensure Cloud root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from main import app
from models.schemas import DeviceTrustState, SessionStatus
from repositories.user_repository import user_repo
from repositories.device_repository import device_repo
from repositories.session_repository import session_repo
from services.identity_service import identity_service
from services.device_service import device_service
from services.security_service import security_service

class TestCloudBackendInfrastructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Generate test Ed25519 keypair
        cls.priv_key = ed25519.Ed25519PrivateKey.generate()
        cls.pub_key = cls.priv_key.public_key()
        cls.pub_pem = cls.pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        cls.test_user_id = "usr_test_cloud_user_001"
        cls.test_device_id = "dev_test_cloud_device_001"
        cls.test_refresh_token = ""
        cls.test_access_token = ""

        # Pre-register user & device for suite
        identity_service.get_or_create_user(user_id=cls.test_user_id, display_name="Test Cloud User")
        device_service.register_device(
            user_id=cls.test_user_id,
            device_name="Test MacBook Air",
            platform="Darwin",
            architecture="arm64",
            os_version="14.5",
            public_key=cls.pub_pem,
            device_id=cls.test_device_id
        )

    def test_01_user_and_device_repositories(self):
        user = user_repo.get_user(self.test_user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, self.test_user_id)

        device = device_repo.get_device(self.test_device_id)
        self.assertIsNotNone(device)
        self.assertEqual(device.device_id, self.test_device_id)
        self.assertEqual(device.trust_state, DeviceTrustState.TRUSTED)

    def test_02_ed25519_device_authentication(self):
        # 1. Get challenge
        res_chl = self.client.post("/api/v1/auth/challenge", json={"device_id": self.test_device_id})
        self.assertEqual(res_chl.status_code, 200)
        nonce = res_chl.json()["challenge"]["nonce"]

        # 2. Sign nonce using Ed25519 private key
        sig_bytes = self.priv_key.sign(nonce.encode("utf-8"))
        sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")

        # 3. Authenticate device
        res_auth = self.client.post("/api/v1/auth/device-auth", json={
            "device_id": self.test_device_id,
            "nonce": nonce,
            "signature_b64": sig_b64
        })
        self.assertEqual(res_auth.status_code, 200, f"Auth response error: {res_auth.text}")
        tokens = res_auth.json()["tokens"]
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)

        TestCloudBackendInfrastructure.test_refresh_token = tokens["refresh_token"]
        TestCloudBackendInfrastructure.test_access_token = tokens["access_token"]

    def test_03_token_refresh_and_revocation(self):
        # Refresh token
        self.assertTrue(bool(self.test_refresh_token), "Refresh token must exist")
        res_ref = self.client.post("/api/v1/auth/token/refresh", json={"refresh_token": self.test_refresh_token})
        self.assertEqual(res_ref.status_code, 200)
        new_tokens = res_ref.json()["tokens"]
        self.assertIn("access_token", new_tokens)

    def test_04_device_trust_management(self):
        # Rename device
        res_rn = self.client.put(f"/api/v1/devices/{self.test_device_id}/rename", json={"new_name": "Test Mac Pro Studio"})
        self.assertEqual(res_rn.status_code, 200)

        # Get device
        res_dev = self.client.get(f"/api/v1/devices/{self.test_device_id}")
        self.assertEqual(res_dev.status_code, 200)
        self.assertEqual(res_dev.json()["device"]["device_name"], "Test Mac Pro Studio")

        # Update trust state to REVOKED
        res_tr = self.client.put(f"/api/v1/devices/{self.test_device_id}/trust", json={"trust_state": "revoked"})
        self.assertEqual(res_tr.status_code, 200)

        # Authentication must fail for revoked device
        nonce = "test_nonce_123"
        sig_bytes = self.priv_key.sign(nonce.encode("utf-8"))
        sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")
        res_fail = self.client.post("/api/v1/auth/device-auth", json={
            "device_id": self.test_device_id,
            "nonce": nonce,
            "signature_b64": sig_b64
        })
        self.assertEqual(res_fail.status_code, 401)

    def test_05_health_readiness_metrics_apis(self):
        # /api/v1/health
        res_h = self.client.get("/api/v1/health")
        self.assertEqual(res_h.status_code, 200)
        self.assertEqual(res_h.json()["status"], "healthy")

        # /api/v1/ready
        res_r = self.client.get("/api/v1/ready")
        self.assertEqual(res_r.status_code, 200)
        self.assertEqual(res_r.json()["status"], "ready")

        # /api/v1/liveness
        res_l = self.client.get("/api/v1/liveness")
        self.assertEqual(res_l.status_code, 200)
        self.assertEqual(res_l.json()["status"], "alive")

        # /api/v1/security/status
        res_sec = self.client.get("/api/v1/security/status")
        self.assertEqual(res_sec.status_code, 200)
        self.assertTrue(res_sec.json()["security_status"]["database_connected"])

        # /api/v1/metrics
        res_m = self.client.get("/api/v1/metrics")
        self.assertEqual(res_m.status_code, 200)
        self.assertIn("jarvis_cloud_users", res_m.text)

if __name__ == "__main__":
    unittest.main()
