"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase P1.3 (Settings & Configuration).
Covers Settings Metadata Registry, Range & Enum Validation, Profile Inheritance, Profile Activation Events,
Resets, Backups & Restores, Export/Import, Multi-User Isolation, EventBus Integration, DIP Compliance, and Schema v3 Migration.
"""
import os
import sys
import time
import inspect
import unittest
import asyncio

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from product.config import ProductConfig
from product.storage import SQLiteProductStorage
from product.settings.settings_models import (
    SettingCategory,
    SettingDataType,
    ThemeOption,
    SettingDefinition,
    SettingValue,
    SettingProfile,
    SettingHistory,
    SettingBackup,
    ValidationResult,
)
from product.settings.settings_store import SQLiteSettingsRepository
from product.settings.settings_validator import SettingsValidator, SETTINGS_REGISTRY
from product.settings.settings_profiles import SettingsProfileManager
from product.settings.settings_events import SettingsEventPublisher
from product.settings.settings_engine import SettingsEngine
from product.settings.settings_interfaces import (
    ISettingsRepository,
    ISettingsValidator,
    ISettingsProfileManager,
)
from brain.event_bus import event_bus


class TestProductPhaseP13(unittest.TestCase):
    """
    Dedicated test suite for Phase P1.3 Settings & Configuration.
    """

    def setUp(self):
        """Set up in-memory storage and isolated SettingsEngine instances."""
        self.config = ProductConfig(db_path=":memory:")
        self.storage = SQLiteProductStorage(db_path=":memory:", config=self.config)
        self.repository = SQLiteSettingsRepository(product_storage_instance=self.storage)
        self.engine = SettingsEngine(repository=self.repository, bus=event_bus)

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up asyncio event loop."""
        self.loop.close()

    # -------------------------------------------------------------------------
    # 1. Settings Metadata Registry Tests
    # -------------------------------------------------------------------------
    def test_01_settings_metadata_registry_defaults(self):
        definitions = self.engine.validator.list_definitions()
        self.assertGreater(len(definitions), 30)

        # Check Assistant settings
        wake_def = self.engine.validator.get_definition("assistant.wake_word")
        self.assertIsNotNone(wake_def)
        self.assertEqual(wake_def.default_value, "JARVIS")

        # Check Voice settings (requires_restart)
        input_def = self.engine.validator.get_definition("voice.input_device")
        self.assertIsNotNone(input_def)
        self.assertTrue(input_def.requires_restart)

    # -------------------------------------------------------------------------
    # 2. Setting Set, Get, and Reset Tests
    # -------------------------------------------------------------------------
    def test_02_setting_set_get_and_reset(self):
        user_id = "usr_tony_p13"

        # Default value before override
        val_default = self.engine.get_setting(user_id, "assistant.speech_volume")
        self.assertEqual(val_default, 80)

        # Set override
        saved_val, val_res = self.engine.set_setting(user_id, "assistant.speech_volume", 95)
        self.assertTrue(val_res.valid)
        self.assertEqual(saved_val.value, 95)

        # Retrieve override
        val_override = self.engine.get_setting(user_id, "assistant.speech_volume")
        self.assertEqual(val_override, 95)

        # Reset override
        self.assertTrue(self.engine.reset_setting(user_id, "assistant.speech_volume"))
        val_after_reset = self.engine.get_setting(user_id, "assistant.speech_volume")
        self.assertEqual(val_after_reset, 80)

    # -------------------------------------------------------------------------
    # 3. Setting Validation Engine Tests
    # -------------------------------------------------------------------------
    def test_03_setting_validation_ranges_enums_types(self):
        # Range check: speech speed (0.5 to 2.0)
        v_speed_ok = self.engine.validate_setting("assistant.speech_speed", 1.5)
        self.assertTrue(v_speed_ok.valid)
        self.assertEqual(v_speed_ok.sanitized_value, 1.5)

        v_speed_invalid = self.engine.validate_setting("assistant.speech_speed", 3.5)
        self.assertFalse(v_speed_invalid.valid)
        self.assertIn("exceeds maximum", v_speed_invalid.error_message)

        # Enum check: theme option
        v_theme_ok = self.engine.validate_setting("appearance.theme", "GLASSMORPHISM")
        self.assertTrue(v_theme_ok.valid)

        v_theme_invalid = self.engine.validate_setting("appearance.theme", "INVALID_THEME")
        self.assertFalse(v_theme_invalid.valid)
        self.assertIn("not in allowed enum options", v_theme_invalid.error_message)

        # Non-empty wake word check
        v_wake_invalid = self.engine.validate_setting("assistant.wake_word", "")
        self.assertFalse(v_wake_invalid.valid)
        self.assertIn("cannot be empty", v_wake_invalid.error_message)

    # -------------------------------------------------------------------------
    # 4. Profile Creation & Inheritance Tests
    # -------------------------------------------------------------------------
    def test_04_profile_creation_and_inheritance(self):
        user_id = "usr_bruce_p13"

        # Default profile
        def_prof = self.engine.profile_manager.ensure_default_profile(user_id)

        # Set base override in Default profile
        self.engine.set_setting(user_id, "assistant.speech_volume", 70, profile_id=def_prof.profile_id)

        # Create child profile 'Coding' inheriting from Default
        coding_prof = self.engine.create_profile(
            user_id=user_id,
            name="Coding",
            description="Coding setup profile",
            parent_profile_id=def_prof.profile_id,
        )

        # Inherited value should be 70
        val_inherited = self.engine.get_setting(user_id, "assistant.speech_volume", profile_id=coding_prof.profile_id)
        self.assertEqual(val_inherited, 70)

        # Override volume only in Coding profile (to 30)
        self.engine.set_setting(user_id, "assistant.speech_volume", 30, profile_id=coding_prof.profile_id)

        # Coding profile should return 30, Default profile should still return 70
        self.assertEqual(self.engine.get_setting(user_id, "assistant.speech_volume", profile_id=coding_prof.profile_id), 30)
        self.assertEqual(self.engine.get_setting(user_id, "assistant.speech_volume", profile_id=def_prof.profile_id), 70)

    # -------------------------------------------------------------------------
    # 5. Profile Switching & Activation Events
    # -------------------------------------------------------------------------
    def test_05_profile_switching_and_activation_event(self):
        user_id = "usr_steve_p13"
        coding_prof = self.engine.create_profile(user_id=user_id, name="Coding Profile")

        # Switch to Coding Profile
        switched = self.engine.switch_profile(user_id, coding_prof.profile_id)
        self.assertTrue(switched.is_active)

        active = self.engine.profile_manager.get_active_profile(user_id)
        self.assertEqual(active.profile_id, coding_prof.profile_id)

    # -------------------------------------------------------------------------
    # 6. Profile Duplication and Deletion
    # -------------------------------------------------------------------------
    def test_06_profile_duplication_and_deletion(self):
        user_id = "usr_natasha_p13"
        meeting_prof = self.engine.create_profile(user_id=user_id, name="Meeting")
        self.engine.set_setting(user_id, "assistant.speech_volume", 20, profile_id=meeting_prof.profile_id)

        # Duplicate profile
        dup_prof = self.engine.duplicate_profile(user_id, meeting_prof.profile_id, "Meeting Copy")
        self.assertEqual(dup_prof.name, "Meeting Copy")
        self.assertEqual(self.engine.get_setting(user_id, "assistant.speech_volume", profile_id=dup_prof.profile_id), 20)

        # Delete meeting profile
        self.assertTrue(self.engine.delete_profile(user_id, meeting_prof.profile_id))
        profiles = self.engine.list_profiles(user_id)
        prof_ids = [p.profile_id for p in profiles]
        self.assertNotIn(meeting_prof.profile_id, prof_ids)

    # -------------------------------------------------------------------------
    # 7. Category & Global Resets
    # -------------------------------------------------------------------------
    def test_07_category_and_global_resets(self):
        user_id = "usr_rhodey_p13"
        self.engine.set_setting(user_id, "assistant.speech_volume", 50)
        self.engine.set_setting(user_id, "assistant.creativity", 90)
        self.engine.set_setting(user_id, "appearance.theme", "LIGHT")

        # Reset ASSISTANT category
        reset_cnt = self.engine.reset_category(user_id, SettingCategory.ASSISTANT)
        self.assertEqual(reset_cnt, 2)
        self.assertEqual(self.engine.get_setting(user_id, "assistant.speech_volume"), 80)
        self.assertEqual(self.engine.get_setting(user_id, "appearance.theme"), "LIGHT")

        # Global Reset All
        reset_all_cnt = self.engine.reset_all(user_id)
        self.assertEqual(reset_all_cnt, 1)
        self.assertEqual(self.engine.get_setting(user_id, "appearance.theme"), "DARK")

    # -------------------------------------------------------------------------
    # 8. Search and List Settings
    # -------------------------------------------------------------------------
    def test_08_search_and_list_settings(self):
        user_id = "usr_clint_p13"
        self.engine.set_setting(user_id, "appearance.theme", "GLASSMORPHISM")

        # List category settings
        app_settings = self.engine.list_settings(user_id, category=SettingCategory.APPEARANCE)
        self.assertEqual(app_settings["appearance.theme"], "GLASSMORPHISM")

        # Search settings by query
        search_res = self.engine.search_settings(user_id, query="speech speed")
        self.assertGreater(len(search_res), 0)
        self.assertEqual(search_res[0]["key"], "assistant.speech_speed")

    # -------------------------------------------------------------------------
    # 9. Setting History Audit
    # -------------------------------------------------------------------------
    def test_09_setting_history_audit(self):
        user_id = "usr_wanda_p13"
        self.engine.set_setting(user_id, "assistant.speech_volume", 60)
        self.engine.set_setting(user_id, "assistant.speech_volume", 90)

        history = self.repository.list_history(user_id, "assistant.speech_volume")
        self.assertGreaterEqual(len(history), 2)
        self.assertEqual(history[0].new_value, 90)

    # -------------------------------------------------------------------------
    # 10. Backups & Restores
    # -------------------------------------------------------------------------
    def test_10_backups_and_restores(self):
        user_id = "usr_vision_p13"
        self.engine.set_setting(user_id, "assistant.speech_volume", 45)

        # Create backup
        backup = self.engine.backup_settings(user_id, "Pre-test Backup")
        self.assertIsNotNone(backup.backup_id)

        # Modify setting
        self.engine.set_setting(user_id, "assistant.speech_volume", 99)
        self.assertEqual(self.engine.get_setting(user_id, "assistant.speech_volume"), 99)

        # Restore backup
        self.assertTrue(self.engine.restore_settings(user_id, backup.backup_id))
        self.assertEqual(self.engine.get_setting(user_id, "assistant.speech_volume"), 45)

    # -------------------------------------------------------------------------
    # 11. Settings Export and Import
    # -------------------------------------------------------------------------
    def test_11_settings_export_and_import(self):
        user_src = "usr_exp_src"
        user_dst = "usr_imp_dst"

        self.engine.set_setting(user_src, "assistant.wake_word", "FRIDAY")

        # Export
        exported_data = self.engine.export_settings(user_src)
        self.assertEqual(exported_data["user_id"], user_src)

        # Import into destination user
        imported_count, msg = self.engine.import_settings(user_dst, exported_data)
        self.assertEqual(imported_count, 1)
        self.assertEqual(self.engine.get_setting(user_dst, "assistant.wake_word"), "FRIDAY")

    # -------------------------------------------------------------------------
    # 12. Multi-User Data Isolation
    # -------------------------------------------------------------------------
    def test_12_multi_user_isolation(self):
        user_a = "usr_alice_p13"
        user_b = "usr_bob_p13"

        self.engine.set_setting(user_a, "assistant.wake_word", "ALICE_WAKE")
        self.engine.set_setting(user_b, "assistant.wake_word", "BOB_WAKE")

        self.assertEqual(self.engine.get_setting(user_a, "assistant.wake_word"), "ALICE_WAKE")
        self.assertEqual(self.engine.get_setting(user_b, "assistant.wake_word"), "BOB_WAKE")

    # -------------------------------------------------------------------------
    # 13. EventBus Integration
    # -------------------------------------------------------------------------
    def test_13_eventbus_integration(self):
        events_received = []

        def listener(evt):
            events_received.append(evt.name)

        event_bus.subscribe("SettingChanged", listener)
        event_bus.subscribe("ProfileCreated", listener)
        event_bus.subscribe("ProfileSwitched", listener)
        event_bus.subscribe("ProfileActivated", listener)
        event_bus.subscribe("SettingReset", listener)

        user_id = "usr_events_p13"
        p = self.engine.create_profile(user_id, "Event Profile")
        self.engine.switch_profile(user_id, p.profile_id)
        self.engine.set_setting(user_id, "assistant.speech_volume", 55)
        self.engine.reset_setting(user_id, "assistant.speech_volume")

        self.assertIn("ProfileCreated", events_received)
        self.assertIn("ProfileSwitched", events_received)
        self.assertIn("ProfileActivated", events_received)
        self.assertIn("SettingChanged", events_received)
        self.assertIn("SettingReset", events_received)

    # -------------------------------------------------------------------------
    # 14. Architecture & Lifecycle Verification
    # -------------------------------------------------------------------------
    def test_14_schema_v3_migration(self):
        schema_ver = self.storage.get_schema_version()
        self.assertEqual(schema_ver, 3)

    def test_15_repository_dip_compliance(self):
        """
        Confirms domain services depend ONLY on abstract repository interfaces
        and contain ZERO direct imports of sqlite3 or SQLiteProductStorage.
        """
        domain_services = [
            SettingsValidator,
            SettingsProfileManager,
            SettingsEventPublisher,
        ]

        for svc in domain_services:
            source = inspect.getsource(svc)
            self.assertNotIn("import sqlite3", source)
            self.assertNotIn("sqlite3.connect", source)
            self.assertNotIn("SQLiteProductStorage", source)

    def test_16_settings_engine_lifecycle_metrics_health(self):
        self.loop.run_until_complete(self.engine.start())
        self.assertTrue(self.engine._running)

        health = self.engine.get_health()
        metrics = self.engine.get_metrics()
        self.assertTrue(health["healthy"])
        self.assertEqual(metrics["phase"], "P1.3")

        self.loop.run_until_complete(self.engine.stop())
        self.assertFalse(self.engine._running)


if __name__ == "__main__":
    unittest.main()
