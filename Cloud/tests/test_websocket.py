import unittest
import base64
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from main import app
from websocket.state_machine import ConnectionState, ConnectionStateMachine
from websocket.protocol import SyncMessageEnvelope, MessageType
from services.identity_service import identity_service
from services.device_service import device_service

class TestWebSocketGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.priv_key = ed25519.Ed25519PrivateKey.generate()
        cls.pub_pem = cls.priv_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        cls.test_user_id = "usr_ws_test_001"
        cls.test_device_id = "dev_ws_test_001"

        identity_service.get_or_create_user(user_id=cls.test_user_id, display_name="WS Test User")
        device_service.register_device(
            user_id=cls.test_user_id,
            device_name="WS Mac",
            platform="Darwin",
            architecture="arm64",
            os_version="14.5",
            public_key=cls.pub_pem,
            device_id=cls.test_device_id
        )

        # Get JWT access token
        res_chl = cls.client.post("/api/v1/auth/challenge", json={"device_id": cls.test_device_id})
        nonce = res_chl.json()["challenge"]["nonce"]
        sig_bytes = cls.priv_key.sign(nonce.encode("utf-8"))
        sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")
        res_auth = cls.client.post("/api/v1/auth/device-auth", json={
            "device_id": cls.test_device_id,
            "nonce": nonce,
            "signature_b64": sig_b64
        })
        cls.access_token = res_auth.json()["tokens"]["access_token"]

    def test_01_state_machine_transitions(self):
        sm = ConnectionStateMachine("conn_test_sm", ConnectionState.CONNECTING)
        self.assertEqual(sm.current_state, ConnectionState.CONNECTING)
        self.assertTrue(sm.transition_to(ConnectionState.AUTHENTICATING))
        self.assertTrue(sm.transition_to(ConnectionState.ACTIVE))
        self.assertTrue(sm.transition_to(ConnectionState.IDLE))
        self.assertTrue(sm.transition_to(ConnectionState.DISCONNECTED))

    def test_02_websocket_authenticated_connection_and_ping_pong(self):
        with self.client.websocket_connect(f"/ws/sync?token={self.access_token}") as websocket:
            # 1. Receive AUTH_OK frame
            data_str = websocket.receive_text()
            env = SyncMessageEnvelope(**json.loads(data_str))
            self.assertEqual(env.message_type, MessageType.AUTH_OK)

            # 2. Send PING frame
            ping_env = SyncMessageEnvelope(
                user_id=self.test_user_id,
                device_id=self.test_device_id,
                sequence_number=1,
                message_type=MessageType.PING,
                payload={"ts": 12345}
            )
            websocket.send_text(json.dumps(ping_env.model_dump()))

            # 3. Receive PONG frame
            pong_str = websocket.receive_text()
            pong_env = SyncMessageEnvelope(**json.loads(pong_str))
            self.assertEqual(pong_env.message_type, MessageType.PONG)

if __name__ == "__main__":
    unittest.main()
