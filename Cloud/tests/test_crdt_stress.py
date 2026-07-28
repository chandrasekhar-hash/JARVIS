import unittest
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sync.crdt import LWWMap, ORSet, CRDTEngine

class TestCRDTStress(unittest.TestCase):
    def test_01_concurrent_lww_map_updates(self):
        engine_A = CRDTEngine()
        engine_B = CRDTEngine()

        # Simulate 100 concurrent updates from 2 devices
        now = time.time()
        for i in range(50):
            engine_A.merge_settings({f"setting_{i}": f"val_A_{i}"}, timestamp=now + i, device_id="dev_A")
            engine_B.merge_settings({f"setting_{i}": f"val_B_{i}"}, timestamp=now + i + 0.001, device_id="dev_B")

        # Merge B into A
        snapshot_B = engine_B.settings.read()
        engine_A.merge_settings(snapshot_B, timestamp=now + 100, device_id="dev_B")

        snapshot_A = engine_A.get_snapshot()
        self.assertEqual(len(snapshot_A["settings"]), 50)
        # dev_B had higher timestamp, so all settings must equal val_B_...
        self.assertEqual(snapshot_A["settings"]["setting_0"], "val_B_0")

    def test_02_concurrent_or_set_add_remove(self):
        orset = ORSet()
        tags = []
        for i in range(20):
            t = orset.add(f"item_{i}", {"name": f"Task {i}"})
            tags.append(t)

        self.assertEqual(len(orset.read()), 20)

        # Remove first 10 items
        for t in tags[:10]:
            orset.remove(t)

        self.assertEqual(len(orset.read()), 10)

if __name__ == "__main__":
    unittest.main()
