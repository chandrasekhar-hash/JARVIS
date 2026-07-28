import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from Client.sync.offline_store import OfflineStore
from Client.sync.replay_queue import ReplayQueue

class TestOfflineOperation(unittest.TestCase):
    def test_01_offline_store_checkpoints_and_cache(self):
        store = OfflineStore(":memory:")
        store.save_checkpoint("usr_off_1", "dev_off_1", last_seq=42, stream_id="1000-0")

        chk = store.get_checkpoint("usr_off_1", "dev_off_1")
        self.assertIsNotNone(chk)
        self.assertEqual(chk["last_sequence_number"], 42)
        self.assertEqual(chk["last_stream_id"], "1000-0")

        store.save_entity_cache("tasks", {"task_1": "Complete Phase 8.4"})
        cache = store.get_entity_cache("tasks")
        self.assertIsNotNone(cache)
        self.assertEqual(cache["task_1"], "Complete Phase 8.4")

    def test_02_replay_queue_buffering(self):
        rq = ReplayQueue()
        rq.enqueue_operation("settings", {"font": "Fira Code"}, sequence_number=1)
        rq.enqueue_operation("memory", {"topic": "AI"}, sequence_number=2)

        self.assertEqual(rq.get_pending_count(), 2)
        ops = rq.drain_and_sort_queue()
        self.assertEqual(len(ops), 2)
        self.assertEqual(rq.get_pending_count(), 0)

if __name__ == "__main__":
    unittest.main()
