import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from Client.sync.conflict_handler import ConflictHandler


class TestConflictHandler(unittest.TestCase):
    def test_01_automatic_crdt_conflict_resolution(self):
        handler = ConflictHandler()
        conflicts = handler.resolve_settings_update({"theme": "synthwave"}, timestamp=100.0, device_id="dev_1")
        self.assertGreaterEqual(conflicts, 0)

    def test_02_create_conflict_review_notification(self):
        handler = ConflictHandler()
        notif = handler.create_review_notification(
            entity_type="settings",
            key="theme",
            local_val="cyberpunk",
            remote_val="synthwave",
            merge_res="synthwave",
            device_source="dev_mobile_02"
        )
        self.assertIsNotNone(notif)
        self.assertEqual(notif.key, "theme")
        self.assertEqual(notif.device_source, "dev_mobile_02")
        self.assertTrue(notif.resolved_automatically)

    def test_03_manual_conflict_resolution_overrides(self):
        handler = ConflictHandler()
        notif = handler.create_review_notification(
            entity_type="settings",
            key="theme",
            local_val={"theme": "cyberpunk"},
            remote_val={"theme": "synthwave"},
            merge_res={"theme": "synthwave"},
            device_source="dev_mobile_02"
        )

        # Test local override
        success_local = handler.user_override_local(notif.conflict_id)
        self.assertTrue(success_local)
        self.assertEqual(notif.manual_resolution, "local")

        # Test remote override
        success_remote = handler.user_override_remote(notif.conflict_id)
        self.assertTrue(success_remote)
        self.assertEqual(notif.manual_resolution, "remote")


if __name__ == "__main__":
    unittest.main()
