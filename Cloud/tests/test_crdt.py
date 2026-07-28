import unittest
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sync.crdt import LWWRegister, ORSet, LWWMap, CRDTEngine

class TestCRDTEngine(unittest.TestCase):
    def test_01_lww_register(self):
        reg = LWWRegister("dark", timestamp=100.0, device_id="dev_A")
        updated = reg.update("light", timestamp=200.0, device_id="dev_B")
        self.assertTrue(updated)
        self.assertEqual(reg.value, "light")

        # Stale update must be rejected
        rejected = reg.update("dim", timestamp=150.0, device_id="dev_C")
        self.assertFalse(rejected)
        self.assertEqual(reg.value, "light")

    def test_02_or_set(self):
        orset = ORSet()
        tag1 = orset.add("task_101", {"title": "Backup Database"})
        tag2 = orset.add("task_102", {"title": "Update Plugins"})

        items = orset.read()
        self.assertEqual(len(items), 2)

        orset.remove(tag1)
        items_after = orset.read()
        self.assertEqual(len(items_after), 1)
        self.assertEqual(items_after[0]["title"], "Update Plugins")

    def test_03_lww_map(self):
        lww_map = LWWMap()
        lww_map.set("user_name", "JARVIS Master", timestamp=100.0, device_id="dev_1")

        other_map = LWWMap()
        other_map.set("user_name", "Chief Architect", timestamp=200.0, device_id="dev_2")
        other_map.set("ai_model", "groq/llama-3.3", timestamp=200.0, device_id="dev_2")

        conflicts = lww_map.merge(other_map)
        self.assertGreater(conflicts, 0)
        read_state = lww_map.read()
        self.assertEqual(read_state["user_name"], "Chief Architect")
        self.assertEqual(read_state["ai_model"], "groq/llama-3.3")

if __name__ == "__main__":
    unittest.main()
