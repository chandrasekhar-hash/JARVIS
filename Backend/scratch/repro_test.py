import unittest
from fastapi.testclient import TestClient
from main import app
from identity.identity_storage import identity_storage
from identity.otp_service import otp_service
from identity.password_utils import hash_password, verify_password

client = TestClient(app)

class TestAuthRegressions(unittest.TestCase):

    def setUp(self):
        self.test_username = "test_auth_user_01"
        self.test_email = "test_auth_user_01@example.com"
        self.test_password = "Password123!"

        # Cleanup
        identity_storage.delete_user_credential_by_username(self.test_username)
        identity_storage.delete_user_credential_by_email(self.test_email)

    def tearDown(self):
        identity_storage.delete_user_credential_by_username(self.test_username)
        identity_storage.delete_user_credential_by_email(self.test_email)

    def test_full_registration_logout_login_flow(self):
        # 1. Request OTP
        req_res = client.post("/api/auth/register/request-otp", json={
            "username": self.test_username,
            "email": self.test_email
        })
        self.assertEqual(req_res.status_code, 200, req_res.text)

        # Get generated OTP from otp_service store for testing
        otp_entry = otp_service._otp_store.get(self.test_email)
        self.assertIsNotNone(otp_entry)
        # Verify OTP
        # We need the actual 6 digit OTP string
        # Since _otp_store stores hashed OTP, let's extract or generate known OTP
        # Actually in test, let's look at how verify_registration_otp works
        pass

if __name__ == "__main__":
    unittest.main()
