import os
import sys
import time
import asyncio
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from user_model.models import (
    PreferenceType,
    CommunicationStyle,
    UserPreference,
    UserHabit,
    WorkflowAffinity,
    ActivityWindow,
    UserConsent,
    UserProfile,
    PreferenceObservation,
)
from user_model.preference_store import PreferenceStore
from user_model.habit_analyzer import HabitAnalyzer
from user_model.profile_manager import ProfileManager
from user_model.provider import UserContextProvider
from brain.event_bus import EventBus


class TestUserModelPhase7(unittest.IsolatedAsyncioTestCase):

    async def test_explicit_preference_crud(self):
        store = PreferenceStore()

        # Record explicit preference
        pref = UserPreference(
            user_id="u1",
            key="editor",
            value="VS Code",
            preference_type=PreferenceType.EXPLICIT,
            confidence=1.0,
        )
        res = store.record_preference(pref)
        self.assertTrue(res.success)
        self.assertEqual(res.preference.key, "editor")

        # Get preference SLA < 20ms
        start = time.perf_counter()
        fetched = store.get_preference("u1", "editor")
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.value, "VS Code")

        # Delete preference
        deleted = store.delete_preference("u1", "editor")
        self.assertTrue(deleted)
        self.assertIsNone(store.get_preference("u1", "editor"))

    async def test_implicit_preference_and_confidence_decay(self):
        store = PreferenceStore()

        # Record implicit preference with lower initial confidence
        pref = UserPreference(
            user_id="u2",
            key="browser",
            value="Chrome",
            preference_type=PreferenceType.IMPLICIT,
            confidence=0.6,
        )
        store.record_preference(pref)

        # Simulate older timestamp for decay testing
        cached_pref = store.get_preference("u2", "browser")
        cached_pref.updated_at = time.time() - 4000.0  # > 1 hour ago

        decayed_count = store.apply_confidence_decay("u2", decay_rate=0.1)
        self.assertEqual(decayed_count, 1)

        decayed_pref = store.get_preference("u2", "browser")
        self.assertLess(decayed_pref.confidence, 0.6)

    async def test_profile_synthesis_and_conflict_resolution(self):
        pref_store = PreferenceStore()
        manager = ProfileManager(preference_store=pref_store)

        # Record implicit preference
        pref_store.record_preference(
            UserPreference(user_id="u3", key="theme", value="light", preference_type=PreferenceType.IMPLICIT, confidence=0.5)
        )
        # Record explicit preference overriding the same key
        pref_store.record_preference(
            UserPreference(user_id="u3", key="theme", value="dark", preference_type=PreferenceType.EXPLICIT, confidence=1.0)
        )

        profile = manager.build_profile("u3")
        self.assertEqual(profile.explicit_preferences.get("theme"), "dark")
        self.assertNotIn("theme", profile.implicit_preferences)  # Explicit overrides implicit

    async def test_habit_analyzer(self):
        analyzer = HabitAnalyzer(min_frequency_threshold=2)

        observations = [
            PreferenceObservation(user_id="u4", observation_key="workflow", observed_value="edit->build->test", category="workflow", timestamp=time.time()),
            PreferenceObservation(user_id="u4", observation_key="workflow", observed_value="edit->build->test", category="workflow", timestamp=time.time()),
        ]

        tool_usages = [
            {"tool_name": "vscode", "count": 5},
            {"tool_name": "git", "count": 3},
        ]

        habit_profile = analyzer.analyze_habits("u4", observations, tool_usages)
        self.assertEqual(len(habit_profile.top_tools), 2)
        self.assertIn("vscode", habit_profile.top_tools)
        self.assertEqual(len(habit_profile.workflow_affinities), 1)

    async def test_consent_management(self):
        pref_store = PreferenceStore()
        manager = ProfileManager(preference_store=pref_store)

        # Opt-out of personalization
        consent = UserConsent(user_id="u5", opt_in_personalization=False)
        manager.update_consent(consent)

        # Recording preferences under disabled consent should fail
        res = pref_store.record_preference(
            UserPreference(user_id="u5", key="lang", value="python"), consent=consent
        )
        self.assertFalse(res.success)
        self.assertIn("Consent disabled", res.error_message)

        # Building profile under disabled consent returns default unpersonalized profile
        profile = manager.build_profile("u5")
        self.assertEqual(len(profile.explicit_preferences), 0)

    async def test_user_context_provider_apis_and_slas(self):
        pref_store = PreferenceStore()
        pref_store.record_preference(UserPreference(user_id="u6", key="editor", value="Neovim"))

        manager = ProfileManager(preference_store=pref_store)
        provider = UserContextProvider(profile_manager=manager, preference_store=pref_store)

        # Test Preference Lookup SLA < 20ms
        start_pref = time.perf_counter()
        prefs = provider.get_preferences("u6")
        pref_ms = (time.perf_counter() - start_pref) * 1000.0
        self.assertLess(pref_ms, 20.0)
        self.assertEqual(prefs.get("editor"), "Neovim")

        # Test Profile Lookup SLA < 100ms
        start_prof = time.perf_counter()
        profile = provider.get_user_profile("u6")
        prof_ms = (time.perf_counter() - start_prof) * 1000.0
        self.assertLess(prof_ms, 100.0)
        self.assertEqual(profile.user_id, "u6")

    async def test_event_publishing(self):
        custom_bus = EventBus()
        events_emitted = []

        def listener(evt):
            events_emitted.append(evt.name)

        custom_bus.subscribe("PreferenceLearned", listener)
        custom_bus.subscribe("PreferenceRemoved", listener)
        custom_bus.subscribe("UserModelUpdated", listener)
        custom_bus.subscribe("ConsentChanged", listener)

        store = PreferenceStore(bus=custom_bus)
        manager = ProfileManager(preference_store=store, bus=custom_bus)

        store.record_preference(UserPreference(user_id="u7", key="k1", value="v1"))
        store.delete_preference("u7", "k1")
        manager.build_profile("u7")
        manager.update_consent(UserConsent(user_id="u7", opt_in_personalization=True))

        await asyncio.sleep(0.05)
        self.assertIn("PreferenceLearned", events_emitted)
        self.assertIn("PreferenceRemoved", events_emitted)
        self.assertIn("UserModelUpdated", events_emitted)
        self.assertIn("ConsentChanged", events_emitted)


if __name__ == "__main__":
    unittest.main()
