import unittest
import time
import os
import secrets
from identity.otp_service import otp_service
from identity.identity_storage import identity_storage
from identity.email_service import email_service
from identity.password_utils import hash_password, verify_password

class TestForgotPasswordOTP(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_username = "fg_test_user_99"
        cls.test_email = "unknownhuman090909@gmail.com"
        cls.test_password_old = "OldPassword123!"
        cls.test_password_new = "NewPassword123!"

        # Ensure clean state
        identity_storage.delete_user_credential_by_username(cls.test_username)
        identity_storage.delete_user_credential_by_email(cls.test_email)

        # Create test user
        cls.hashed_pwd = hash_password(cls.test_password_old)
        identity_storage.save_user_credential(
            username=cls.test_username,
            email=cls.test_email,
            password_hash=cls.hashed_pwd,
            display_name="FG Test User",
            is_verified=1
        )

    @classmethod
    def tearDownClass(cls):
        identity_storage.delete_user_credential_by_username(cls.test_username)

    def test_01_anti_enumeration(self):
        # Non-existent identifier
        user = identity_storage.get_user_credential_by_identifier("non_existent_user_xyz")
        self.assertIsNone(user)

    def test_02_generate_and_verify_forgot_password_otp(self):
        # Clear existing OTP
        if self.test_email in otp_service._otp_store:
            del otp_service._otp_store[self.test_email]

        # Generate OTP
        otp, err = otp_service.generate_password_reset_otp(self.test_email)
        self.assertIsNone(err)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

        # Test 123456 rejected unless coincidentally generated
        if otp != "123456":
            success, token, err = otp_service.verify_password_reset_otp(self.test_email, "123456")
            self.assertFalse(success)
            self.assertIsNone(token)
            self.assertIn("Invalid verification code", err)

        # Test correct OTP
        success, reset_token, err = otp_service.verify_password_reset_otp(self.test_email, otp)
        self.assertTrue(success)
        self.assertIsNotNone(reset_token)
        self.assertIsNone(err)

        # Verify OTP is single-use and invalidated immediately
        success_retry, _, _ = otp_service.verify_password_reset_otp(self.test_email, otp)
        self.assertFalse(success_retry)

        # Test single-use reset token consumption
        consumed = otp_service.consume_password_reset_token(reset_token, self.test_email)
        self.assertTrue(consumed)

        # Second consumption attempt fails
        consumed_again = otp_service.consume_password_reset_token(reset_token, self.test_email)
        self.assertFalse(consumed_again)

    def test_03_password_reset_and_session_invalidation(self):
        # Generate and verify OTP
        if self.test_email in otp_service._otp_store:
            del otp_service._otp_store[self.test_email]

        otp, _ = otp_service.generate_password_reset_otp(self.test_email)
        success, reset_token, _ = otp_service.verify_password_reset_otp(self.test_email, otp)
        self.assertTrue(success)

        # Reset password
        new_pwd_hash = hash_password(self.test_password_new)
        updated = identity_storage.update_user_password(self.test_email, new_pwd_hash)
        self.assertTrue(updated)

        # Invalidate sessions
        identity_storage.revoke_all_user_sessions(self.test_email)

        # Verify old password fails
        user_record = identity_storage.get_user_credential_by_username(self.test_username)
        self.assertFalse(verify_password(self.test_password_old, user_record["password_hash"]))

        # Verify new password succeeds
        self.assertTrue(verify_password(self.test_password_new, user_record["password_hash"]))

if __name__ == "__main__":
    unittest.main()
