import unittest
import time
from identity.otp_service import otp_service
from identity.email_service import email_service

class TestRegistrationOTPFlow(unittest.TestCase):

    def test_01_otp_generation_and_security(self):
        email = "test_user_otp@example.com"
        otp, err = otp_service.generate_registration_otp(email)
        self.assertIsNone(err)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

        # Verify resend cooldown (30 seconds)
        otp2, err2 = otp_service.generate_registration_otp(email)
        self.assertIn("Please wait", err2)

    def test_02_otp_verification(self):
        email = "test_verify_otp@example.com"
        otp, _ = otp_service.generate_registration_otp(email)
        
        # Test wrong OTP
        success, token, err = otp_service.verify_registration_otp(email, "000000")
        self.assertFalse(success)
        self.assertIsNone(token)
        self.assertIn("Invalid verification code", err)

        # Test correct OTP
        success, token, err = otp_service.verify_registration_otp(email, otp)
        self.assertTrue(success)
        self.assertIsNotNone(token)

        # Test single-use (OTP should be consumed/invalidated)
        success2, token2, err2 = otp_service.verify_registration_otp(email, otp)
        self.assertFalse(success2)

        # Consume verification token
        consumed = otp_service.consume_verification_token(token, email)
        self.assertTrue(consumed)

        # Token cannot be consumed twice
        consumed_again = otp_service.consume_verification_token(token, email)
        self.assertFalse(consumed_again)

    def test_03_mock_123456_rejected(self):
        email = "test_mock_rejection@example.com"
        otp, _ = otp_service.generate_registration_otp(email)
        
        if otp != "123456":
            success, token, err = otp_service.verify_registration_otp(email, "123456")
            self.assertFalse(success)
            self.assertIsNone(token)

if __name__ == "__main__":
    unittest.main()
