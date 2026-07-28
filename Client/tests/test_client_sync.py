import unittest
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from Client.sync.sync_manager import ClientSyncManager
from Client.sync.offline_store import OfflineStore
from Client.sync.replay_queue import ReplayQueue
from Client.sync.protocol import ClientSyncEnvelope, ClientMessageType


class TestClientSyncManager(unittest.TestCase):
    def setUp(self):
        self.store = OfflineStore(":memory:")
        self.queue = ReplayQueue(store=self.store)
        self.mgr = ClientSyncManager(store=self.store, queue=self.queue)
        self.mgr.initialize_client("usr_client_001", "dev_client_001", "token_access", "token_refresh")

    def test_01_submit_local_change_offline_queueing(self):
        # When WS client is offline, local changes must be enqueued in ReplayQueue & SQLite
        res = self.mgr.submit_local_change("settings", {"theme": "cyberpunk", "sound": True})
        self.assertEqual(res["status"], "queued_offline")
        self.assertEqual(self.queue.get_pending_count(), 1)

        # Check offline store cache
        cache = self.store.get_entity_cache("settings")
        self.assertIsNotNone(cache)

    def test_02_replay_offline_queue(self):
        self.mgr.submit_local_change("memory", {"fact_1": "User loves Python"})
        self.assertEqual(self.queue.get_pending_count(), 1)

        # Simulate WS client connected
        self.mgr.ws_client.is_connected = True

        replayed = asyncio.run(self.mgr.replay_offline_queue())
        self.assertEqual(replayed, 1)

    def test_03_incoming_ack_durable_removal(self):
        res = self.mgr.submit_local_change("settings", {"font": "Fira Code"})
        op_id = res["op_id"]
        self.assertEqual(self.queue.get_pending_count(), 1)

        # Receive ACK envelope from Cloud Gateway
        ack_env = ClientSyncEnvelope(
            user_id="usr_client_001",
            device_id="dev_client_001",
            sequence_number=1,
            message_type=ClientMessageType.ACK,
            payload={"op_id": op_id, "status": "processed"}
        )
        self.mgr._handle_incoming_envelope(ack_env)

        # Pending count should drop to 0 after durable ACK
        self.assertEqual(self.queue.get_pending_count(), 0)


if __name__ == "__main__":
    unittest.main()
