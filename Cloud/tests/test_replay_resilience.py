import unittest
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sync.replay import replay_engine
from sync.checkpoint import checkpoint_manager, CheckpointMetadata

class TestReplayResilience(unittest.TestCase):
    def test_01_out_of_order_and_duplicate_delivery(self):
        user_id = "usr_resilience_001"
        device_id = "dev_resilience_001"

        # Checkpoint sequence = 10
        chk = CheckpointMetadata(
            user_id=user_id,
            device_id=device_id,
            last_sequence_number=10,
            timestamp=time.time()
        )
        checkpoint_manager.save_checkpoint(chk)

        # Queue out of order events: msg_12 (seq 12), msg_11 (seq 11), duplicate msg_11
        replay_engine.queue_offline_update(device_id, {"message_id": "msg_12", "sequence_number": 12, "data": "second"})
        replay_engine.queue_offline_update(device_id, {"message_id": "msg_11", "sequence_number": 11, "data": "first"})
        replay_engine.queue_offline_update(device_id, {"message_id": "msg_11", "sequence_number": 11, "data": "duplicate"})

        # Replay events
        replayed = replay_engine.replay_offline_events(user_id, device_id)

        # Must sort chronologically: msg_11 first, then msg_12, excluding duplicate
        self.assertEqual(len(replayed), 2)
        self.assertEqual(replayed[0]["message_id"], "msg_11")
        self.assertEqual(replayed[1]["message_id"], "msg_12")

    def test_02_idempotent_deduplication(self):
        msg_id = "idempotent_test_key_001"
        self.assertFalse(replay_engine.is_duplicate(msg_id))
        replay_engine.mark_processed(msg_id)
        self.assertTrue(replay_engine.is_duplicate(msg_id))

if __name__ == "__main__":
    unittest.main()
