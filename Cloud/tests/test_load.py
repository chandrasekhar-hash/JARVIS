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

class TestLoadAndPerformanceBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.priv_key = ed25519.Ed25519PrivateKey.generate()
        cls.pub_pem = cls.priv_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        cls.user_id = "usr_load_test_001"
        cls.device_id = "dev_load_test_001"

        identity_service.get_or_create_user(user_id=cls.user_id, display_name="Load Test User")
        device_service.register_device(
            user_id=cls.user_id,
            device_name="Load Studio",
            platform="Darwin",
            architecture="arm64",
            os_version="14.5",
            public_key=cls.pub_pem,
            device_id=cls.device_id
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

    def test_01_load_and_latency_benchmark(self):
        latencies = []
        message_count = 50

        start_time = time.time()
        with self.client.websocket_connect(f"/ws/sync?token={self.access_token}") as websocket:
            # Read AUTH_OK
            websocket.receive_text()

            for i in range(message_count):
                msg_start = time.time()
                ping_env = SyncMessageEnvelope(
                    user_id=self.user_id,
                    device_id=self.device_id,
                    sequence_number=i + 1,
                    message_type=MessageType.PING,
                    payload={"seq": i}
                )
                websocket.send_text(json.dumps(ping_env.model_dump()))
                pong_str = websocket.receive_text()
                msg_end = time.time()
                latencies.append((msg_end - msg_start) * 1000.0)  # ms

        total_duration = time.time() - start_time
        latencies.sort()
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = latencies[int(len(latencies) * 0.95)]
        p99_latency = latencies[int(len(latencies) * 0.99)]
        throughput = message_count / total_duration

        print(f"\n--- LOAD & PERFORMANCE BENCHMARK REPORT ---")
        print(f"Messages Processed: {message_count}")
        print(f"Total Duration: {total_duration:.3f}s")
        print(f"Throughput: {throughput:.2f} msg/sec")
        print(f"Average Latency: {avg_latency:.3f} ms")
        print(f"P95 Latency: {p95_latency:.3f} ms")
        print(f"P99 Latency: {p99_latency:.3f} ms")
        print(f"-------------------------------------------\n")

        # Target: avg latency < 50ms
        self.assertLess(avg_latency, 50.0)

if __name__ == "__main__":
    unittest.main()
