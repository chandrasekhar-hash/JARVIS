import time
import json
import base64
import unittest
import asyncio
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from Cloud.intelligence.offloader import RemoteInferenceOffloader, remote_offloader
from Cloud.intelligence.circuit_breaker import CircuitBreaker
from Cloud.services.context_mesh_service import ContextMeshService, context_mesh_service
from Cloud.services.presence_service import PresenceService, presence_service
from Cloud.intelligence.remote_agent import RemoteAgentService, remote_agent_service
from Cloud.services.job_orchestrator import JobOrchestrator, job_orchestrator
from Cloud.services.cloud_scheduler_relay import CloudSchedulerRelay, cloud_scheduler_relay
from Cloud.services.notification_service import NotificationMeshService, notification_service


class TestRemoteIntelligenceSubsystem(unittest.TestCase):

    def setUp(self):
        self.user_id = "usr_test_intel_123"
        self.device_id = "dev_test_desktop_456"

    def test_01_remote_inference_offloader_and_circuit_breaker(self):
        async def run_test():
            offloader = RemoteInferenceOffloader()
            # 1. Execute sync inference
            res = await offloader.execute_remote_inference(
                prompt="Summarize today's architecture plan.",
                preferred_provider="groq"
            )
            self.assertEqual(res["provider"], "groq")
            self.assertIn("Groq Cloud Response", res["text"])
            self.assertTrue(res["trace_id"].startswith("trc_inf_"))

            # 2. Stream inference
            stream_tokens = []
            async for token in offloader.stream_remote_inference("Hello world"):
                stream_tokens.append(token)
            self.assertTrue(len(stream_tokens) > 0)

            # 3. Test CircuitBreaker failover
            offloader.circuit_breakers["groq"].state = "OPEN"
            offloader.circuit_breakers["groq"].last_state_change = time.time()
            res_failover = await offloader.execute_remote_inference(
                prompt="Test failover",
                preferred_provider="groq"
            )
            self.assertEqual(res_failover["provider"], "gemini")

        asyncio.run(run_test())

    def test_02_context_mesh_service(self):
        cms = ContextMeshService()
        snap1 = cms.submit_snapshot(
            user_id=self.user_id,
            device_id=self.device_id,
            context_type="desktop_screen",
            data={"active_app": "VSCode", "file": "main.py"},
            ttl_seconds=300.0,
            confidence=0.95
        )
        self.assertEqual(snap1.version, 1)

        snap2 = cms.submit_snapshot(
            user_id=self.user_id,
            device_id=self.device_id,
            context_type="desktop_screen",
            data={"active_app": "Terminal", "file": "test.py"},
            ttl_seconds=300.0,
            confidence=0.98
        )
        self.assertEqual(snap2.version, 2)

        header = cms.get_formatted_context_header(self.user_id)
        self.assertIn("[CROSS-DEVICE ACTIVE CONTEXT]", header)
        self.assertIn("Terminal", header)

    def test_03_presence_service(self):
        async def run_test():
            ps = PresenceService()
            await ps.update_presence(
                device_id=self.device_id,
                user_id=self.user_id,
                new_status="CONNECTED",
                capabilities=["desktop_execution", "llm_offload"],
                workload_score=0.2
            )
            self.assertTrue(ps.is_device_online(self.device_id))
            p_info = ps.get_presence(self.device_id)
            self.assertEqual(p_info["status"], "CONNECTED")
            self.assertEqual(p_info["workload_score"], 0.2)

        asyncio.run(run_test())

    def test_04_cryptographic_remote_agent_trust(self):
        # Generate Ed25519 Keypair for test device
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        pub_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        ras = RemoteAgentService()
        payload = {
            "action": "open_application",
            "app_name": "Terminal",
            "timestamp": time.time(),
            "nonce": "nonce_test_9999",
            "capabilities": ["desktop_execution"]
        }
        canonical = json.dumps(payload, sort_keys=True).encode("utf-8")
        sig_bytes = private_key.sign(canonical)

        # 1. Valid Signature & Nonce
        verified = ras.verify_remote_command_payload(payload, pub_pem, sig_bytes)
        self.assertTrue(verified)

        # 2. Replay attack rejection (Same Nonce)
        verified_replay = ras.verify_remote_command_payload(payload, pub_pem, sig_bytes)
        self.assertFalse(verified_replay)

    def test_05_job_orchestrator(self):
        async def run_test():
            jo = JobOrchestrator()
            job = jo.create_job(
                user_id=self.user_id,
                origin_device_id=self.device_id,
                task_type="remote_script",
                payload={"script": "echo Hello"}
            )
            self.assertEqual(job.status, "QUEUED")

            async def dummy_task():
                return {"result": "success"}

            res = await jo.execute_job(job.job_id, dummy_task)
            self.assertEqual(res["status"], "COMPLETED")
            self.assertEqual(jo.get_job(job.job_id).status, "COMPLETED")

        asyncio.run(run_test())

    def test_06_cloud_scheduler_relay(self):
        async def run_test():
            ps = PresenceService()
            # Device offline
            ps.device_presence[self.device_id] = {
                "status": "OFFLINE",
                "user_id": self.user_id,
                "last_heartbeat": 0.0
            }

            csr = CloudSchedulerRelay(p_service=ps)
            csr.register_scheduled_task(
                task_id="task_daily_briefing",
                user_id=self.user_id,
                origin_device_id=self.device_id,
                task_name="Daily Morning Briefing",
                schedule_cron="0 8 * * *",
                task_payload={"type": "briefing"}
            )

            relayed = await csr.check_and_relay_offline_tasks(self.user_id)
            self.assertEqual(len(relayed), 1)
            self.assertEqual(relayed[0]["status"], "COMPLETED")

        asyncio.run(run_test())

    def test_07_notification_mesh_service(self):
        async def run_test():
            nms = NotificationMeshService()
            notif = await nms.dispatch_notification(
                user_id=self.user_id,
                title="Task Completed",
                body="Cloud relay task executed successfully.",
                category="info"
            )
            self.assertEqual(notif["status"], "unread")

            unread = nms.get_notifications(self.user_id, unread_only=True)
            self.assertEqual(len(unread), 1)

            nms.mark_as_read(self.user_id, notif["notification_id"])
            unread_after = nms.get_notifications(self.user_id, unread_only=True)
            self.assertEqual(len(unread_after), 0)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
