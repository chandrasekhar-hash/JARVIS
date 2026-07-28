import unittest
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sync.replay import replay_engine
from sync.checkpoint import checkpoint_manager, CheckpointMetadata

class TestReplayEngine(unittest.TestCase):
    def test_01_queue_and_replay_offline_events(self):
        user_id = "usr_replay_001"
        device_id = "dev_replay_001"

        # Save checkpoint last_sequence_number = 2
        chk = CheckpointMetadata(
            user_id=user_id,
            device_id=device_id,
            last_sequence_number=2,
            timestamp=time.time()
        )
        checkpoint_manager.save_checkpoint(chk)

        # Queue 3 events with sequence numbers 1, 2, 3
        replay_engine.queue_offline_update(device_id, {"message_id": "m1", "sequence_number": 1, "data": "stale"})
        replay_engine.queue_offline_update(device_id, {"message_id": "m2", "sequence_number": 2, "data": "exact"})
        replay_engine.queue_offline_update(device_id, {"message_id": "m3", "sequence_number": 3, "data": "new"})

        # Replay events
        replayed = replay_engine.replay_offline_events(user_id, device_id)
        # Events with sequence_number > 2 (i.e. msg 3) should be replayed
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0]["message_id"], "m3")

    def test_02_deduplication(self):
        replay_engine.mark_processed("dup_msg_100")
        self.assertTrue(replay_engine.is_duplicate("dup_msg_100"))
        self.assertFalse(replay_engine.is_duplicate("dup_msg_999"))

if __name__ == "__main__":
    unittest.main()
