import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from identity.identity_storage import identity_storage
from identity.password_utils import hash_password

client = TestClient(app)

class TestDeleteAccountEndpoint(unittest.TestCase):

    def setUp(self):
        self.username = "del_api_user_99"
        self.email = "del_api_user_99@example.com"
        self.password = "CorrectPass123!"
        self.wrong_password = "WrongPass123!"

        identity_storage.delete_user_credential_by_username(self.username)
        identity_storage.delete_user_credential_by_email(self.email)

        # Create user credential
        hashed = hash_password(self.password)
        identity_storage.save_user_credential(
            username=self.username,
            email=self.email,
            password_hash=hashed,
            display_name="Delete API User",
            is_verified=1
        )

    def tearDown(self):
        identity_storage.delete_user_credential_by_username(self.username)
        identity_storage.delete_user_credential_by_email(self.email)

    def test_delete_account_endpoint_flow(self):
        # 1. Login to get authenticated session cookies
        login_res = client.post("/api/auth/login", json={
            "username": self.username,
            "password": self.password
        })
        self.assertEqual(login_res.status_code, 200, login_res.text)

        # Extract cookies from login response
        cookies = login_res.cookies

        # 2. Call delete account with WRONG password
        wrong_res = client.post("/api/account/delete", json={
            "password": self.wrong_password
        }, cookies=cookies)
        self.assertEqual(wrong_res.status_code, 400)
        self.assertEqual(wrong_res.json().get("detail"), "Incorrect password.")
        print("Wrong password test: PASSED (Returns 'Incorrect password.')")

        # 3. Call delete account with CORRECT password
        correct_res = client.post("/api/account/delete", json={
            "password": self.password
        }, cookies=cookies)
        self.assertEqual(correct_res.status_code, 200, correct_res.text)
        self.assertEqual(correct_res.json().get("status"), "success")
        print("Correct password test: PASSED (Account deleted successfully)")

        # 4. Verify account deleted in database
        user_rec = identity_storage.get_user_credential_by_username(self.username)
        self.assertIsNone(user_rec)
        print("Database cleanup verification: PASSED")

if __name__ == "__main__":
    unittest.main()
