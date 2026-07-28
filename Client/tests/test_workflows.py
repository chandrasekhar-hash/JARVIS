import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from Client.services.cloud_sync_service import CloudSyncService
from Client.sync.sync_manager import ClientSyncManager
from Client.sync.offline_store import OfflineStore
from Client.sync.replay_queue import ReplayQueue

class TestClientWorkflows(unittest.TestCase):
    def test_01_cloud_sync_service_full_workflow(self):
        store = OfflineStore(":memory:")
        queue = ReplayQueue()
        mgr = ClientSyncManager(store=store, queue=queue)
        service = CloudSyncService(manager=mgr)

        service.initialize("usr_wf_1", "dev_wf_1", "access_1", "refresh_1")

        # 1. Sync Settings offline
        res_settings = service.sync_settings({"theme": "dark_pro"})
        self.assertEqual(res_settings["status"], "queued_offline")

        # 2. Sync Memory offline
        res_mem = service.sync_memory({"user_name": "JARVIS Lead Architect"})
        self.assertEqual(res_mem["status"], "queued_offline")

        # 3. Force Sync (Replays queued updates)
        mgr.ws_client.is_connected = True
        res_force = service.force_sync()
        self.assertEqual(res_force["replayed_offline_ops"], 2)

        # 4. Check Status
        status = service.get_status()
        self.assertEqual(status["pending_offline_ops"], 0)

        service.shutdown()

if __name__ == "__main__":
    unittest.main()
