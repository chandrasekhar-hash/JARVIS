import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_auth_no_otp():
    session = requests.Session()
    unique_suffix = "test_no_otp_99"
    test_username = f"user_{unique_suffix}"
    test_email = f"{unique_suffix}@example.com"
    test_password = "Password123!"

    print("--- 1. Testing Invalid Email Format ---")
    resp = session.post(f"{BASE_URL}/api/auth/register", json={
        "username": test_username,
        "email": "invalid_email_format",
        "password": test_password
    })
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    assert resp.status_code == 400
    assert "valid email" in resp.json()["detail"].lower()

    print("\n--- 2. Testing Weak Password ---")
    resp = session.post(f"{BASE_URL}/api/auth/register", json={
        "username": test_username,
        "email": test_email,
        "password": "weak"
    })
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    assert resp.status_code == 400
    assert "security requirements" in resp.json()["detail"].lower()

    print("\n--- 3. Testing Valid Registration ---")
    resp = session.post(f"{BASE_URL}/api/auth/register", json={
        "username": test_username,
        "email": test_email,
        "password": test_password,
        "display_name": "No OTP User"
    })
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    print("\n--- 4. Testing Duplicate Username ---")
    resp = session.post(f"{BASE_URL}/api/auth/register", json={
        "username": test_username,
        "email": f"diff_{test_email}",
        "password": test_password
    })
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    assert resp.status_code == 400
    assert "already taken" in resp.json()["detail"].lower()

    print("\n--- 5. Testing Duplicate Email ---")
    resp = session.post(f"{BASE_URL}/api/auth/register", json={
        "username": f"diff_{test_username}",
        "email": test_email,
        "password": test_password
    })
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"].lower()

    print("\n--- 6. Testing Successful Login ---")
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "username": test_username,
        "password": test_password,
        "remember_me": True
    })
    print(f"Status: {resp.status_code}, Cookies: {dict(session.cookies)}")
    assert resp.status_code == 200
    assert "jarvis_access_token" in session.cookies

    print("\n--- 7. Testing Session Refresh ---")
    resp = session.post(f"{BASE_URL}/api/session/refresh")
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    assert resp.status_code == 200

    print("\n--- 8. Testing Profile Update ---")
    resp = session.patch(f"{BASE_URL}/api/auth/profile", json={
        "display_name": "Updated No OTP User"
    })
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    assert resp.status_code == 200
    assert resp.json()["user"]["display_name"] == "Updated No OTP User"

    print("\n--- 9. Testing Forgot Password Endpoint ---")
    resp = session.post(f"{BASE_URL}/api/auth/forgot-password", json={
        "email": test_email
    })
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    assert resp.status_code == 400
    assert "currently unavailable" in resp.json()["detail"].lower()

    print("\n--- 10. Testing Logout ---")
    resp = session.post(f"{BASE_URL}/api/session/logout")
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200

    print("\nALL BACKEND AUTH TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    test_auth_no_otp()
