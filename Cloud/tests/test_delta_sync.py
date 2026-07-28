import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sync.delta_engine import delta_engine
from sync.crdt import crdt_engine

class TestDeltaSyncEngine(unittest.TestCase):
    def test_01_create_and_apply_delta_patch(self):
        user_id = "usr_delta_001"
        device_id = "dev_delta_001"
        changes = {"theme": "cyberpunk", "fontSize": 14}

        patch_wrapper = delta_engine.create_delta_patch(
            user_id=user_id,
            device_id=device_id,
            entity_type="settings",
            changes=changes,
            encrypt=True
        )
        self.assertTrue(patch_wrapper["encrypted"])

        success, conflicts = delta_engine.apply_delta_patch(patch_wrapper, device_id)
        self.assertTrue(success)
        snapshot = crdt_engine.get_snapshot()
        self.assertEqual(snapshot["settings"]["theme"], "cyberpunk")

    def test_02_threshold_compression_policy(self):
        user_id = "usr_delta_002"
        device_id = "dev_delta_002"
        # Large payload >= 1 KB
        large_memory = {f"fact_{i}": f"User preference detail information number {i} stored in memory timeline context" for i in range(50)}

        patch_wrapper = delta_engine.create_delta_patch(
            user_id=user_id,
            device_id=device_id,
            entity_type="memory",
            changes=large_memory,
            encrypt=True
        )
        self.assertTrue(patch_wrapper["payload"]["compressed"])

        success, conflicts = delta_engine.apply_delta_patch(patch_wrapper, device_id)
        self.assertTrue(success)
        snapshot = crdt_engine.get_snapshot()
        self.assertIn("fact_0", snapshot["memory"])

if __name__ == "__main__":
    unittest.main()
