import unittest
import base64
import json
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from main import app
from websocket.protocol import SyncMessageEnvelope, MessageType
from services.identity_service import identity_service
from services.device_service import device_service
from sync.crdt import crdt_engine
from sync.delta_engine import delta_engine

class TestEndToEndMultiDeviceSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user_id = "usr_e2e_sync_001"
        identity_service.get_or_create_user(user_id=cls.user_id, display_name="E2E Sync User")

        # Setup Device 1 (Desktop Studio)
        cls.priv_key_1 = ed25519.Ed25519PrivateKey.generate()
        cls.pub_pem_1 = cls.priv_key_1.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        cls.dev_id_1 = "dev_e2e_desktop_01"
        device_service.register_device(
            user_id=cls.user_id, device_name="Desktop Studio", platform="Darwin",
            architecture="arm64", os_version="14.5", public_key=cls.pub_pem_1, device_id=cls.dev_id_1
        )
        cls.token_1 = cls._get_device_jwt(cls.dev_id_1, cls.priv_key_1)

        # Setup Device 2 (Mobile Companion)
        cls.priv_key_2 = ed25519.Ed25519PrivateKey.generate()
        cls.pub_pem_2 = cls.priv_key_2.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        cls.dev_id_2 = "dev_e2e_mobile_02"
        device_service.register_device(
            user_id=cls.user_id, device_name="Mobile Companion", platform="iOS",
            architecture="arm64", os_version="17.4", public_key=cls.pub_pem_2, device_id=cls.dev_id_2
        )
        cls.token_2 = cls._get_device_jwt(cls.dev_id_2, cls.priv_key_2)

    @classmethod
    def _get_device_jwt(cls, device_id: str, priv_key: ed25519.Ed25519PrivateKey) -> str:
        res_chl = cls.client.post("/api/v1/auth/challenge", json={"device_id": device_id})
        nonce = res_chl.json()["challenge"]["nonce"]
        sig_bytes = priv_key.sign(nonce.encode("utf-8"))
        sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")
        res_auth = cls.client.post("/api/v1/auth/device-auth", json={
            "device_id": device_id,
            "nonce": nonce,
            "signature_b64": sig_b64
        })
        return res_auth.json()["tokens"]["access_token"]

    def test_01_desktop_to_mobile_sync(self):
        """Simulates Desktop updating settings delta patch, broadcasted to Mobile."""
        with self.client.websocket_connect(f"/ws/sync?token={self.token_1}") as ws_desktop:
            ws_desktop.receive_text()  # AUTH_OK

            with self.client.websocket_connect(f"/ws/sync?token={self.token_2}") as ws_mobile:
                ws_mobile.receive_text()  # AUTH_OK

                # Desktop sends DELTA patch
                patch_wrapper = delta_engine.create_delta_patch(
                    user_id=self.user_id,
                    device_id=self.dev_id_1,
                    entity_type="settings",
                    changes={"theme": "dark_mode_pro", "sound": True},
                    encrypt=True
                )
                delta_env = SyncMessageEnvelope(
                    user_id=self.user_id,
                    device_id=self.dev_id_1,
                    sequence_number=1,
                    message_type=MessageType.DELTA,
                    payload=patch_wrapper
                )
                ws_desktop.send_text(json.dumps(delta_env.model_dump()))

                # Desktop receives frames (may receive DEVICE_JOIN before ACK)
                ack_env = None
                for _ in range(3):
                    frame_str = ws_desktop.receive_text()
                    env = SyncMessageEnvelope(**json.loads(frame_str))
                    if env.message_type == MessageType.ACK:
                        ack_env = env
                        break

                self.assertIsNotNone(ack_env)
                self.assertEqual(ack_env.message_type, MessageType.ACK)

                # Mobile receives broadcasted DELTA frame
                delta_received = None
                for _ in range(3):
                    frame_str = ws_mobile.receive_text()
                    env = SyncMessageEnvelope(**json.loads(frame_str))
                    if env.message_type == MessageType.DELTA:
                        delta_received = env
                        break

                self.assertIsNotNone(delta_received)
                self.assertEqual(delta_received.message_type, MessageType.DELTA)

                # Verify CRDT state merged cleanly
                snapshot = crdt_engine.get_snapshot()
                self.assertEqual(snapshot["settings"]["theme"], "dark_mode_pro")

    def test_02_simultaneous_edits_resolution(self):
        """Simulates simultaneous edits on identical records from Desktop and Mobile."""
        patch_1 = delta_engine.create_delta_patch(self.user_id, self.dev_id_1, "memory", {"fact_A": "Desktop Value"}, encrypt=True)
        patch_2 = delta_engine.create_delta_patch(self.user_id, self.dev_id_2, "memory", {"fact_A": "Mobile Value"}, encrypt=True)

        # Apply both patches concurrently
        delta_engine.apply_delta_patch(patch_1, self.dev_id_1)
        delta_engine.apply_delta_patch(patch_2, self.dev_id_2)

        snapshot = crdt_engine.get_snapshot()
        self.assertIn("fact_A", snapshot["memory"])
        self.assertTrue(snapshot["memory"]["fact_A"] in ["Desktop Value", "Mobile Value"])

if __name__ == "__main__":
    unittest.main()
