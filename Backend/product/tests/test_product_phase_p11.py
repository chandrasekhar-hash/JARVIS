"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase P1.1 (Identity & User Management).
Covering Authentication, Login/Logout, User Profiles, Sessions, Preferences, Security,
Security Audit Logging, Role-Based Model, Schema Versioning, and Repository Dependency Verification.
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
from product.models import (
    User,
    Role,
    AccountStatus,
    UserProfile,
    UserPreferences,
    VoiceSettings,
    NotificationSettings,
    PrivacySettings,
    Session,
    AuthResult,
    SecurityContext,
)
from product.security import (
    PasswordHasher,
    TokenGenerator,
    InputValidator,
    SlidingWindowRateLimiter,
    SecurityProvider,
)
from product.audit import (
    AuditLevel,
    AuditEvent,
    AuditEntry,
    SecurityAuditLogger,
)
from product.storage import SQLiteProductStorage
from product.users import UserManager
from product.profiles import ProfileManager
from product.sessions import SessionManager
from product.preferences import PreferenceManager
from product.authentication import AuthenticationService
from product.coordinator import ProductCoordinator
from product.engine import ProductEngine
from product.interfaces import (
    IUserRepository,
    IProfileRepository,
    ISessionRepository,
    IPreferenceRepository,
    IPasswordResetRepository,
    IAuditRepository,
)
from brain.event_bus import event_bus


class TestProductPhaseP11(unittest.TestCase):
    """
    Dedicated test suite for Phase P1.1 Identity & User Management.
    """

    def setUp(self):
        """Set up in-memory storage and isolated instances for testing."""
        self.config = ProductConfig(
            db_path=":memory:",
            max_failed_login_attempts=3,
            account_lockout_seconds=60,
            session_timeout_seconds=3600,
            remember_me_expiration_seconds=86400,
            rate_limit_max_attempts=5,
            rate_limit_window_seconds=10,
        )
        self.storage = SQLiteProductStorage(db_path=":memory:", config=self.config)
        self.coordinator = ProductCoordinator(config=self.config, storage=self.storage, bus=event_bus)
        self.engine = ProductEngine(config=self.config, coordinator=self.coordinator, bus=event_bus)

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up asyncio event loop."""
        self.loop.close()

    # -------------------------------------------------------------------------
    # 1. Security Tests
    # -------------------------------------------------------------------------
    def test_01_password_hashing_and_verification(self):
        hasher = PasswordHasher(self.config)
        password = "SecurePassword123!"
        hash_hex, salt_hex = hasher.hash_password(password)

        self.assertIsNotNone(hash_hex)
        self.assertIsNotNone(salt_hex)
        self.assertTrue(hasher.verify_password(password, hash_hex, salt_hex))
        self.assertFalse(hasher.verify_password("WrongPassword123!", hash_hex, salt_hex))

    def test_02_input_validation(self):
        validator = InputValidator(self.config)

        # Email validation
        valid, _ = validator.validate_email("user@example.com")
        self.assertTrue(valid)
        invalid, _ = validator.validate_email("invalid-email-string")
        self.assertFalse(invalid)

        # Username validation
        valid_u, _ = validator.validate_username("tony_stark")
        self.assertTrue(valid_u)
        invalid_u, _ = validator.validate_username("a")  # too short
        self.assertFalse(invalid_u)

        # Password validation
        valid_p, _ = validator.validate_password("StarkPass2026")
        self.assertTrue(valid_p)
        invalid_p, _ = validator.validate_password("weak")
        self.assertFalse(invalid_p)

    def test_03_sliding_window_rate_limiter(self):
        limiter = SlidingWindowRateLimiter(max_attempts=3, window_seconds=10)
        id_test = "ip_127.0.0.1"

        self.assertTrue(limiter.is_allowed(id_test)[0])
        self.assertTrue(limiter.is_allowed(id_test)[0])
        self.assertTrue(limiter.is_allowed(id_test)[0])
        # 4th request should be blocked
        allowed, msg = limiter.is_allowed(id_test)
        self.assertFalse(allowed)
        self.assertIn("Rate limit exceeded", msg)

    # -------------------------------------------------------------------------
    # 2. User Creation & Management Tests
    # -------------------------------------------------------------------------
    def test_04_user_registration(self):
        res = self.engine.register_user(
            username="tonystark",
            email="tony@starkindustries.com",
            password="ArcReactor2026!",
            display_name="Tony Stark",
        )

        self.assertTrue(res.success)
        self.assertIsNotNone(res.user_profile)
        self.assertEqual(res.user_profile.username, "tonystark")
        self.assertEqual(res.user_profile.display_name, "Tony Stark")
        self.assertIsNotNone(res.preferences)
        self.assertEqual(res.preferences.wake_word, "JARVIS")

    def test_05_duplicate_user_and_email_prevention(self):
        self.engine.register_user(
            username="pepperpotts",
            email="pepper@starkindustries.com",
            password="CEO_Password123!",
        )

        # Duplicate username attempt
        res1 = self.engine.register_user(
            username="pepperpotts",
            email="other@starkindustries.com",
            password="AnotherPassword123!",
        )
        self.assertFalse(res1.success)
        self.assertEqual(res1.error_code, "USERNAME_EXISTS")

        # Duplicate email attempt
        res2 = self.engine.register_user(
            username="otheruser",
            email="pepper@starkindustries.com",
            password="AnotherPassword123!",
        )
        self.assertFalse(res2.success)
        self.assertEqual(res2.error_code, "EMAIL_EXISTS")

    # -------------------------------------------------------------------------
    # 3. Login & Authentication Tests
    # -------------------------------------------------------------------------
    def test_06_successful_login(self):
        self.engine.register_user(
            username="rhodey",
            email="rhodey@usaf.gov",
            password="WarMachine123!",
        )

        # Login with username
        res1 = self.engine.login("rhodey", "WarMachine123!")
        self.assertTrue(res1.success)
        self.assertIsNotNone(res1.session_token)
        self.assertIsNotNone(res1.user_profile)

        # Login with email
        res2 = self.engine.login("rhodey@usaf.gov", "WarMachine123!")
        self.assertTrue(res2.success)
        self.assertIsNotNone(res2.session_token)

    def test_07_failed_login_and_account_lockout(self):
        self.engine.register_user(
            username="brucebanner",
            email="bruce@avengers.org",
            password="HulkSmash2026!",
        )

        # 3 Failed login attempts
        self.assertFalse(self.engine.login("brucebanner", "WrongPass1").success)
        self.assertFalse(self.engine.login("brucebanner", "WrongPass2").success)
        self.assertFalse(self.engine.login("brucebanner", "WrongPass3").success)

        # 4th attempt with CORRECT password should fail due to account lockout
        res = self.engine.login("brucebanner", "HulkSmash2026!")
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, "ACCOUNT_LOCKED")

    def test_08_password_reset_flow(self):
        self.engine.register_user(
            username="peterparker",
            email="peter@dailybugle.com",
            password="WebSlinger2026!",
        )

        # Request reset
        success, reset_token = self.engine.request_password_reset("peterparker")
        self.assertTrue(success)
        self.assertTrue(reset_token.startswith("rst_"))

        # Confirm reset with weak password (should fail validation)
        succ_fail, msg_fail = self.engine.confirm_password_reset(reset_token, "weak")
        self.assertFalse(succ_fail)

        # Confirm reset with strong password
        succ_pass, msg_pass = self.engine.confirm_password_reset(reset_token, "NewSpiderSuit2026!")
        self.assertTrue(succ_pass)

        # Login with old password should fail
        self.assertFalse(self.engine.login("peterparker", "WebSlinger2026!").success)

        # Login with new password should succeed
        self.assertTrue(self.engine.login("peterparker", "NewSpiderSuit2026!").success)

    # -------------------------------------------------------------------------
    # 4. Session Management Tests
    # -------------------------------------------------------------------------
    def test_09_session_validation_and_logout(self):
        reg = self.engine.register_user(
            username="natasharomanoff",
            email="natasha@shield.gov",
            password="BlackWidow2026!",
        )
        login_res = self.engine.login("natasharomanoff", "BlackWidow2026!")
        token = login_res.session_token

        # Validate session
        val_res = self.engine.validate_session(token)
        self.assertTrue(val_res.success)
        self.assertEqual(val_res.user_profile.username, "natasharomanoff")

        # Logout
        self.assertTrue(self.engine.logout(token))

        # Validate session after logout should fail
        self.assertFalse(self.engine.validate_session(token).success)

    def test_10_remember_me_token_flow(self):
        self.engine.register_user(
            username="clintbarton",
            email="clint@hawkeye.org",
            password="Bullseye2026!",
        )
        login_res = self.engine.login("clintbarton", "Bullseye2026!", remember_me=True)
        remember_token = login_res.remember_me_token
        self.assertIsNotNone(remember_token)

        # Auto-login via remember-me token
        auto_res = self.engine.login_with_remember_token(remember_token, device_id="laptop_01")
        self.assertTrue(auto_res.success)
        self.assertEqual(auto_res.user_profile.username, "clintbarton")
        self.assertIsNotNone(auto_res.session_token)

    def test_11_multiple_device_sessions_and_revocation(self):
        self.engine.register_user(
            username="steverodgers",
            email="steve@avengers.org",
            password="CaptainAmerica2026!",
        )

        s1 = self.engine.login("steverodgers", "CaptainAmerica2026!", device_id="dev_mobile")
        s2 = self.engine.login("steverodgers", "CaptainAmerica2026!", device_id="dev_desktop")

        user_id = s1.user_profile.user_id
        active_sessions = self.engine.get_active_sessions(user_id)
        self.assertEqual(len(active_sessions), 2)

        # Revoke mobile session
        self.assertTrue(self.engine.revoke_session(s1.session.session_id))

        remaining = self.engine.get_active_sessions(user_id)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].device_id, "dev_desktop")

    # -------------------------------------------------------------------------
    # 5. User Profile Tests
    # -------------------------------------------------------------------------
    def test_12_profile_updates(self):
        reg = self.engine.register_user(
            username="nickfury",
            email="fury@shield.gov",
            password="DirectorFury2026!",
            display_name="Director Fury",
        )
        user_id = reg.user_profile.user_id

        # Update profile fields
        updated = self.engine.update_profile(
            user_id=user_id,
            display_name="Nicholas J. Fury",
            avatar="http://avatar.shield.gov/fury.png",
            theme_preference="glassmorphism",
            language_preference="en-GB",
        )

        self.assertEqual(updated.display_name, "Nicholas J. Fury")
        self.assertEqual(updated.avatar, "http://avatar.shield.gov/fury.png")
        self.assertEqual(updated.theme_preference, "glassmorphism")
        self.assertEqual(updated.language_preference, "en-GB")

        # Fetch profile
        fetched = self.engine.get_profile(user_id)
        self.assertEqual(fetched.display_name, "Nicholas J. Fury")

    # -------------------------------------------------------------------------
    # 6. User Preferences Tests
    # -------------------------------------------------------------------------
    def test_13_user_preferences_crud(self):
        reg = self.engine.register_user(
            username="wandamaximoff",
            email="wanda@avengers.org",
            password="ScarletWitch2026!",
        )
        user_id = reg.user_profile.user_id

        # Retrieve default preferences
        prefs = self.engine.get_preferences(user_id)
        self.assertEqual(prefs.wake_word, "JARVIS")
        self.assertEqual(prefs.voice_settings.voice_id, "en-US-Neural")

        # Update custom preferences
        updated = self.engine.update_preferences(
            user_id=user_id,
            wake_word="FRIDAY",
            assistant_name="F.R.I.D.A.Y.",
            preferred_ai_model="gemini-2.5-pro",
            preferred_language="en-GB",
        )

        self.assertEqual(updated.wake_word, "FRIDAY")
        self.assertEqual(updated.assistant_name, "F.R.I.D.A.Y.")
        self.assertEqual(updated.preferred_ai_model, "gemini-2.5-pro")
        self.assertEqual(updated.preferred_language, "en-GB")

    # -------------------------------------------------------------------------
    # 7. Integration & Lifecycle Tests
    # -------------------------------------------------------------------------
    def test_14_product_engine_lifecycle_metrics_and_events(self):
        events_received = []

        def listener(evt):
            events_received.append(evt.name)

        event_bus.subscribe("UserRegistered", listener)
        event_bus.subscribe("UserAuthenticated", listener)
        event_bus.subscribe("UserLoggedOut", listener)

        # Start Engine
        self.loop.run_until_complete(self.engine.start())
        self.assertTrue(self.engine._running)

        # Register User (Triggers UserRegistered)
        self.engine.register_user(
            username="vision_ai",
            email="vision@avengers.org",
            password="MindStone2026!",
        )

        # Login User (Triggers UserAuthenticated)
        login_res = self.engine.login("vision_ai", "MindStone2026!")
        self.assertTrue(login_res.success)

        # Logout User (Triggers UserLoggedOut)
        self.engine.logout(login_res.session_token)

        # Stop Engine
        self.loop.run_until_complete(self.engine.stop())
        self.assertFalse(self.engine._running)

        # Check Health & Metrics
        health = self.engine.get_health()
        metrics = self.engine.get_metrics()
        self.assertEqual(health["subsystem"], "ProductLayer.Identity")
        self.assertIn("db_path", metrics)

        # Verify Event Bus triggers
        self.assertIn("UserRegistered", events_received)
        self.assertIn("UserAuthenticated", events_received)
        self.assertIn("UserLoggedOut", events_received)

    # -------------------------------------------------------------------------
    # 8. Pre-Audit Refinement Tests
    # -------------------------------------------------------------------------
    def test_15_security_audit_logger_creation_and_append(self):
        audit_logger = SecurityAuditLogger(repository=self.storage, config=self.config)

        # Record events
        entry1 = audit_logger.record_event(
            event_type=AuditEvent.LOGIN_SUCCESS,
            user_id="usr_audit_01",
            severity=AuditLevel.INFO,
            result="SUCCESS",
        )
        entry2 = audit_logger.record_event(
            event_type=AuditEvent.LOGIN_FAILED,
            user_id="usr_audit_01",
            severity=AuditLevel.WARNING,
            result="FAILURE",
            metadata={"reason": "Invalid password"},
        )

        self.assertIsNotNone(entry1.audit_id)
        self.assertEqual(entry1.event_type, "LOGIN_SUCCESS")
        self.assertEqual(entry2.event_type, "LOGIN_FAILED")

        # Query append-only logs via repository
        logs = self.storage.query_audit_logs(user_id="usr_audit_01")
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].event_type, "LOGIN_FAILED")
        self.assertEqual(logs[1].event_type, "LOGIN_SUCCESS")

    def test_16_role_defaults_serialization_and_validation(self):
        # Default role should be USER
        reg1 = self.engine.register_user(
            username="standard_user",
            email="user@stark.com",
            password="StandardUser2026!",
        )
        user_id = reg1.user_profile.user_id
        user1 = self.coordinator.user_manager.get_user_by_id(user_id)
        self.assertEqual(user1.role, Role.USER)
        self.assertEqual(user1.to_dict()["role"], "USER")

        # Custom role ADMIN
        reg2 = self.engine.register_user(
            username="admin_user",
            email="admin@stark.com",
            password="AdminUser2026!",
            role=Role.ADMIN,
        )
        admin_id = reg2.user_profile.user_id
        user2 = self.coordinator.user_manager.get_user_by_id(admin_id)
        self.assertEqual(user2.role, Role.ADMIN)
        self.assertEqual(user2.to_dict()["role"], "ADMIN")

        # Custom role DEVELOPER
        reg3 = self.engine.register_user(
            username="dev_user",
            email="dev@stark.com",
            password="DevUser2026!",
            role=Role.DEVELOPER,
        )
        dev_id = reg3.user_profile.user_id
        user3 = self.coordinator.user_manager.get_user_by_id(dev_id)
        self.assertEqual(user3.role, Role.DEVELOPER)

        # SecurityContext verification
        login_res = self.engine.login("admin_user", "AdminUser2026!")
        sec_ctx = self.engine.get_security_context(login_res.session_token)
        self.assertIn("ADMIN", sec_ctx.roles)
        self.assertTrue(sec_ctx.has_permission("custom_permission"))

    def test_17_schema_version_metadata(self):
        schema_ver = self.storage.get_schema_version()
        self.assertEqual(schema_ver, 1)

    def test_18_repository_dependency_verification(self):
        """
        Architecture Verification:
        Confirms that domain service classes depend ONLY on abstract repository interfaces
        and contain ZERO direct dependencies or imports of SQLiteProductStorage or sqlite3.
        """
        domain_services = [
            UserManager,
            ProfileManager,
            SessionManager,
            PreferenceManager,
            AuthenticationService,
        ]

        for svc in domain_services:
            source = inspect.getsource(svc)
            self.assertNotIn("import sqlite3", source)
            self.assertNotIn("sqlite3.connect", source)
            self.assertNotIn("SQLiteProductStorage", source)

        # Inspect constructors for abstract interface type hints
        user_mgr_sig = inspect.signature(UserManager.__init__)
        self.assertEqual(user_mgr_sig.parameters["repository"].annotation, IUserRepository)

        profile_mgr_sig = inspect.signature(ProfileManager.__init__)
        self.assertEqual(profile_mgr_sig.parameters["repository"].annotation, IProfileRepository)

        session_mgr_sig = inspect.signature(SessionManager.__init__)
        self.assertEqual(session_mgr_sig.parameters["repository"].annotation, ISessionRepository)

        pref_mgr_sig = inspect.signature(PreferenceManager.__init__)
        self.assertEqual(pref_mgr_sig.parameters["repository"].annotation, IPreferenceRepository)


if __name__ == "__main__":
    unittest.main()
