import unittest
import os
import sys
import sqlite3
import shutil
import tempfile
from alembic.config import Config
from alembic import command

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Cloud.database.schema_verifier import SchemaVerifier, EXPECTED_HEAD_REVISION
from Cloud.database.migration_lock import MigrationLockManager


class TestAlembicMigrationsAndGovernance(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_alembic.db")
        self.db_url = f"sqlite:///{self.db_path}"

        self.ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../alembic.ini"))
        self.alembic_cfg = Config(self.ini_path)
        self.alembic_cfg.set_main_option("script_location", os.path.abspath(os.path.join(os.path.dirname(__file__), "../alembic")))
        self.alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)

        self.verifier = SchemaVerifier(self.db_url)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_fresh_database_migration(self):
        # Run upgrade head on fresh database
        command.upgrade(self.alembic_cfg, "head")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = set(row[0] for row in cursor.fetchall())
        conn.close()

        expected = {"cloud_users", "cloud_devices", "cloud_sessions", "cloud_audit_logs", "cloud_configurations", "alembic_version"}
        self.assertTrue(expected.issubset(tables))

    def test_02_legacy_ddl_validation_and_stamping(self):
        # Create legacy database structure manually
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE cloud_schema_version (version TEXT PRIMARY KEY, applied_at REAL, description TEXT)")
        cursor.execute("INSERT INTO cloud_schema_version VALUES ('v1_cloud_backend', 100.0, 'legacy')")
        cursor.execute("CREATE TABLE cloud_users (user_id TEXT PRIMARY KEY, display_name TEXT, email TEXT, avatar_url TEXT, created_at REAL, updated_at REAL, preferences_json TEXT)")
        cursor.execute("CREATE TABLE cloud_devices (device_id TEXT PRIMARY KEY, user_id TEXT, device_name TEXT, platform TEXT, architecture TEXT, os_version TEXT, app_version TEXT, public_key TEXT, public_key_fingerprint TEXT, trust_state TEXT, created_at REAL, updated_at REAL)")
        cursor.execute("CREATE TABLE cloud_sessions (session_id TEXT PRIMARY KEY, user_id TEXT, device_id TEXT, access_token TEXT, refresh_token TEXT, expires_at REAL, refresh_expires_at REAL, created_at REAL, status TEXT, ip_address TEXT, user_agent TEXT)")
        cursor.execute("CREATE TABLE cloud_audit_logs (log_id TEXT PRIMARY KEY, event_type TEXT, user_id TEXT, device_id TEXT, action TEXT, status TEXT, details_json TEXT, timestamp REAL)")
        cursor.execute("CREATE TABLE cloud_configurations (config_key TEXT PRIMARY KEY, config_value TEXT, updated_at REAL)")
        conn.commit()

        # Validate legacy schema
        isValid = self.verifier.validate_legacy_schema(conn)
        conn.close()
        self.assertTrue(isValid)

        # Stamp baseline revision
        command.stamp(self.alembic_cfg, EXPECTED_HEAD_REVISION)

        curr_rev = self.verifier.get_current_revision()
        self.assertEqual(curr_rev, EXPECTED_HEAD_REVISION)

    def test_03_legacy_schema_mismatch_abort(self):
        # Create incomplete legacy database structure (missing cloud_configurations)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE cloud_schema_version (version TEXT PRIMARY KEY, applied_at REAL, description TEXT)")
        cursor.execute("CREATE TABLE cloud_users (user_id TEXT PRIMARY KEY)")
        conn.commit()

        isValid = self.verifier.validate_legacy_schema(conn)
        conn.close()

        # Verification must fail and return False
        self.assertFalse(isValid)

    def test_04_upgrade_downgrade_cycle(self):
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        self.assertEqual(self.verifier.get_current_revision(), EXPECTED_HEAD_REVISION)

        # Downgrade to base
        command.downgrade(self.alembic_cfg, "base")
        self.assertIsNone(self.verifier.get_current_revision())

        # Upgrade back to head
        command.upgrade(self.alembic_cfg, "head")
        self.assertEqual(self.verifier.get_current_revision(), EXPECTED_HEAD_REVISION)

    def test_05_idempotent_repeated_upgrades(self):
        command.upgrade(self.alembic_cfg, "head")
        command.upgrade(self.alembic_cfg, "head")
        self.assertEqual(self.verifier.get_current_revision(), EXPECTED_HEAD_REVISION)

    def test_06_production_startup_verification_failure(self):
        os.environ["ENVIRONMENT"] = "production"
        try:
            # Uninitialized DB in production mode should halt startup
            success, msg = self.verifier.apply_or_verify_migrations()
            self.assertFalse(success)
            self.assertIn("PRODUCTION STARTUP HALTED", msg)
        finally:
            os.environ["ENVIRONMENT"] = "development"

    def test_07_migration_lock_concurrency(self):
        lock_mgr1 = MigrationLockManager(self.db_url)
        lock_mgr2 = MigrationLockManager(self.db_url)

        self.assertTrue(lock_mgr1.acquire_lock(timeout_seconds=2.0))
        # Second lock acquisition attempt should fail while first lock is held
        self.assertFalse(lock_mgr2.acquire_lock(timeout_seconds=0.5))

        lock_mgr1.release_lock()
        # Second lock acquisition attempt succeeds after first lock released
        self.assertTrue(lock_mgr2.acquire_lock(timeout_seconds=2.0))
        lock_mgr2.release_lock()

    def test_08_corrupted_alembic_version_handling(self):
        # Create corrupted alembic_version table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE alembic_version (invalid_col TEXT)")
        cursor.execute("INSERT INTO alembic_version VALUES ('invalid_rev')")
        conn.commit()
        conn.close()

        rev = self.verifier.get_current_revision()
        self.assertIsNone(rev)


if __name__ == "__main__":
    unittest.main()
