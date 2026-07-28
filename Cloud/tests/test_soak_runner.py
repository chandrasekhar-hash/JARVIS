import unittest
import base64
import json
import time
import os
import sys
import psutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from main import app
from websocket.protocol import SyncMessageEnvelope, MessageType
from services.identity_service import identity_service
from services.device_service import device_service

class TestLongDurationSoakRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.priv_key = ed25519.Ed25519PrivateKey.generate()
        cls.pub_pem = cls.priv_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        cls.user_id = "usr_soak_001"
        cls.device_id = "dev_soak_001"

        identity_service.get_or_create_user(user_id=cls.user_id, display_name="Soak User")
        device_service.register_device(
            user_id=cls.user_id, device_name="Soak Device", platform="Darwin",
            architecture="arm64", os_version="14.5", public_key=cls.pub_pem, device_id=cls.device_id
        )

        res_chl = cls.client.post("/api/v1/auth/challenge", json={"device_id": cls.device_id})
        nonce = res_chl.json()["challenge"]["nonce"]
        sig_bytes = cls.priv_key.sign(nonce.encode("utf-8"))
        sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")
        res_auth = cls.client.post("/api/v1/auth/device-auth", json={
            "device_id": cls.device_id,
            "nonce": nonce,
            "signature_b64": sig_b64
        })
        cls.access_token = res_auth.json()["tokens"]["access_token"]

    def test_01_continuous_soak_sync_iterations(self):
        process = psutil.Process(os.getpid())
        initial_mem = process.memory_info().rss / (1024 * 1024)  # MB

        iterations = 100
        reconnect_every = 20

        print(f"\n--- SOAK TEST RUNNER (100 Iterations, Reconnect Every 20) ---")
        ws = self.client.websocket_connect(f"/ws/sync?token={self.access_token}")
        ws.__enter__()
        ws.receive_text()  # Read AUTH_OK

        try:
            for i in range(iterations):
                if i > 0 and i % reconnect_every == 0:
                    # Periodic reconnect
                    ws.__exit__(None, None, None)
                    ws = self.client.websocket_connect(f"/ws/sync?token={self.access_token}")
                    ws.__enter__()
                    ws.receive_text()

                ping_env = SyncMessageEnvelope(
                    user_id=self.user_id, device_id=self.device_id, sequence_number=i + 1,
                    message_type=MessageType.PING, payload={"soak_iter": i}
                )
                ws.send_text(json.dumps(ping_env.model_dump()))
                ws.receive_text()  # Read PONG

        finally:
            try:
                ws.__exit__(None, None, None)
            except Exception:
                pass

        final_mem = process.memory_info().rss / (1024 * 1024)  # MB
        mem_diff = final_mem - initial_mem

        print(f"Initial Memory: {initial_mem:.2f} MB")
        print(f"Final Memory: {final_mem:.2f} MB")
        print(f"Memory Growth Delta: {mem_diff:.2f} MB")
        print(f"-------------------------------------------\n")

        # Memory growth must be under 20 MB over 100 iterations
        self.assertLess(mem_diff, 20.0)

if __name__ == "__main__":
    unittest.main()
