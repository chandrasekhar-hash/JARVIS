import unittest
from identity.identity_storage import identity_storage
from identity.password_utils import hash_password, verify_password

from identity.identity_models import UserProfile

class TestAccountDeletion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_username = "del_test_user_77"
        cls.test_email = "del_test_user_77@example.com"
        cls.test_password = "SecurePassword123!"

        # Ensure clean state
        identity_storage.delete_user_credential_by_username(cls.test_username)
        identity_storage.delete_user_credential_by_email(cls.test_email)

        # Create test user credentials and profile
        cls.hashed_pwd = hash_password(cls.test_password)
        identity_storage.save_user_credential(
            username=cls.test_username,
            email=cls.test_email,
            password_hash=cls.hashed_pwd,
            display_name="Delete Test User",
            is_verified=1
        )
        identity_storage.save_user_profile(
            UserProfile(
                user_id=cls.test_username,
                display_name="Delete Test User",
                email=cls.test_email
            )
        )

    @classmethod
    def tearDownClass(cls):
        identity_storage.delete_user_credential_by_username(cls.test_username)
        identity_storage.delete_user_credential_by_email(cls.test_email)

    def test_01_user_exists_and_password_validation(self):
        user_record = identity_storage.get_user_credential_by_username(self.test_username)
        self.assertIsNotNone(user_record)
        self.assertEqual(user_record["email"], self.test_email)

        # Test incorrect password fails
        self.assertFalse(verify_password("WrongPassword123!", user_record["password_hash"]))

        # Test correct password succeeds
        self.assertTrue(verify_password(self.test_password, user_record["password_hash"]))

    def test_02_account_deletion_clears_database(self):
        # Perform account deletion
        deleted_by_user = identity_storage.delete_user_credential_by_username(self.test_username)
        self.assertTrue(deleted_by_user)

        # Verify lookup returns None
        user_by_username = identity_storage.get_user_credential_by_username(self.test_username)
        self.assertIsNone(user_by_username)

        user_by_email = identity_storage.get_user_credential_by_email(self.test_email)
        self.assertIsNone(user_by_email)

        user_by_identifier = identity_storage.get_user_credential_by_identifier(self.test_username)
        self.assertIsNone(user_by_identifier)

if __name__ == '__main__':
    unittest.main()
