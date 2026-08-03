import sys
import os
import unittest

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from identity.identity_storage import identity_storage
from identity.otp_service import otp_service
from identity.password_utils import hash_password, verify_password

client = TestClient(app)

class TestE2EAuthFlow(unittest.TestCase):

    def setUp(self):
        self.username = "e2e_user_99"
        self.email = "e2e_user_99@example.com"
        self.password = "SecurePass123!"
        self.new_password = "NewSecurePass123!"

        identity_storage.delete_user_credential_by_username(self.username)
        identity_storage.delete_user_credential_by_email(self.email)

    def tearDown(self):
        identity_storage.delete_user_credential_by_username(self.username)
        identity_storage.delete_user_credential_by_email(self.email)

    def test_full_registration_and_forgot_password_cycle(self):
        print("\n--- 1. REGISTRATION: REQUEST OTP ---")
        res1 = client.post("/api/auth/register/request-otp", json={
            "username": self.username,
            "email": self.email
        })
        self.assertEqual(res1.status_code, 200, res1.text)

        # Inspect OTP generated internally
        otp_record = otp_service._otp_store.get(self.email)
        self.assertIsNotNone(otp_record)
        print("OTP generated successfully in memory.")

        # Re-generate OTP for verification test
        # Since _otp_store holds hashed OTP, we can test verify_registration_otp directly or patch
        # Let's inspect generate_registration_otp return value
        del otp_service._otp_store[self.email]
        real_otp, err = otp_service.generate_registration_otp(self.email)
        self.assertIsNone(err)
        self.assertEqual(len(real_otp), 6)

        print("\n--- 2. REGISTRATION: VERIFY OTP ---")
        res2 = client.post("/api/auth/register/verify-otp", json={
            "email": self.email,
            "otp": real_otp
        })
        self.assertEqual(res2.status_code, 200, res2.text)
        data2 = res2.json()
        verification_token = data2["verification_token"]
        self.assertTrue(verification_token)

        print("\n--- 3. REGISTRATION: CREATE PASSWORD ---")
        res3 = client.post("/api/auth/register", json={
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "verification_token": verification_token
        })
        self.assertEqual(res3.status_code, 200, res3.text)

        print("\n--- 4. DATABASE INSPECTION ---")
        user_record = identity_storage.get_user_credential_by_username(self.username)
        self.assertIsNotNone(user_record)
        print(f"User exists: YES")
        print(f"Password hash exists: {'YES' if user_record.get('password_hash') else 'NO'}")
        print(f"Hash length: {len(user_record.get('password_hash', ''))}")
        print(f"Algorithm: PBKDF2-HMAC-SHA256")
        print(f"Account verified: {user_record.get('is_verified') == 1}")
        print(f"Registration completed: YES")

        print("\n--- 5. INITIAL LOGIN ---")
        res_login1 = client.post("/api/auth/login", json={
            "username": self.username,
            "password": self.password
        })
        self.assertEqual(res_login1.status_code, 200, res_login1.text)

        print("\n--- 6. LOGOUT ---")
        res_logout = client.post("/api/session/logout")
        self.assertEqual(res_logout.status_code, 200, res_logout.text)

        print("\n--- 7. LOGIN AGAIN AFTER LOGOUT ---")
        res_login2 = client.post("/api/auth/login", json={
            "username": self.username,
            "password": self.password
        })
        self.assertEqual(res_login2.status_code, 200, res_login2.text)
        print("Login again after logout: PASSED")

        print("\n--- 8. FORGOT PASSWORD: REQUEST OTP ---")
        res_fp1 = client.post("/api/auth/forgot-password/request-otp", json={
            "identifier": self.username
        })
        self.assertEqual(res_fp1.status_code, 200, res_fp1.text)

        del otp_service._otp_store[self.email]
        fp_otp, err = otp_service.generate_password_reset_otp(self.email)
        self.assertIsNone(err)

        print("\n--- 9. FORGOT PASSWORD: VERIFY OTP ---")
        res_fp2 = client.post("/api/auth/forgot-password/verify-otp", json={
            "identifier": self.username,
            "otp": fp_otp
        })
        self.assertEqual(res_fp2.status_code, 200, res_fp2.text)
        reset_token = res_fp2.json()["reset_token"]
        self.assertTrue(reset_token)

        print("\n--- 10. FORGOT PASSWORD: RESET PASSWORD ---")
        res_fp3 = client.post("/api/auth/forgot-password/reset-password", json={
            "identifier": self.username,
            "reset_token": reset_token,
            "new_password": self.new_password
        })
        self.assertEqual(res_fp3.status_code, 200, res_fp3.text)

        print("\n--- 11. LOGIN WITH OLD PASSWORD (MUST FAIL) ---")
        res_old = client.post("/api/auth/login", json={
            "username": self.username,
            "password": self.password
        })
        self.assertEqual(res_old.status_code, 401, "Old password should be rejected")

        print("\n--- 12. LOGIN WITH NEW PASSWORD (MUST SUCCEED) ---")
        res_new = client.post("/api/auth/login", json={
            "username": self.username,
            "password": self.new_password
        })
        self.assertEqual(res_new.status_code, 200, res_new.text)
        print("Forgot password reset & login with new password: PASSED")

if __name__ == "__main__":
    unittest.main()
