import re
import time
import logging
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional

from identity.identity_manager import identity_manager
from identity.identity_storage import identity_storage
from identity.password_utils import hash_password, verify_password
from identity.jwt_manager import (
    create_jwt_token, 
    verify_jwt_token, 
    ACCESS_TOKEN_EXPIRE_SECONDS, 
    REFRESH_TOKEN_EXPIRE_SECONDS
)

logger = logging.getLogger("jarvis_auth")

router = APIRouter(prefix="/api", tags=["Auth & Session"])

# Email validation regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
# Special characters regex
SPECIAL_CHAR_REGEX = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]")

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: Optional[str] = None

class LoginRequest(BaseModel):
    username: str  # Carries Username or Email
    password: str
    remember_me: Optional[bool] = False

class ForgotPasswordRequest(BaseModel):
    email: str

@router.post("/auth/register")
def register_user(body: RegisterRequest):
    clean_username = body.username.strip()
    clean_email = body.email.strip().lower()
    password = body.password

    # 1. Username validation
    if not clean_username:
        raise HTTPException(status_code=400, detail="Username is required.")

    # 2. Email format validation
    if not clean_email or not EMAIL_REGEX.match(clean_email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")

    # 3. Password requirements validation (Min 8 chars, 1 uppercase, 1 special char)
    if len(password) < 8 or not re.search(r"[A-Z]", password) or not SPECIAL_CHAR_REGEX.search(password):
        raise HTTPException(status_code=400, detail="Password does not meet the security requirements.")

    # 4. Duplicate username check
    existing_user_by_name = identity_storage.get_user_credential_by_username(clean_username)
    if existing_user_by_name:
        raise HTTPException(status_code=400, detail="This username is already taken.")

    # 5. Duplicate email check
    existing_user_by_email = identity_storage.get_user_credential_by_email(clean_email)
    if existing_user_by_email:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # 6. Secure Password Hashing (PBKDF2-HMAC-SHA256)
    hashed_pwd = hash_password(password)

    # 7. Save user credential with is_verified=1 so user is active & verified
    user_record = identity_storage.save_user_credential(
        username=clean_username,
        email=clean_email,
        password_hash=hashed_pwd,
        display_name=body.display_name or clean_username,
        is_verified=1
    )

    return {
        "status": "success",
        "message": "Account created successfully. Please log in.",
        "user": {
            "username": clean_username,
            "email": clean_email,
            "display_name": body.display_name or clean_username
        }
    }

@router.post("/auth/login")
def login_user(body: LoginRequest, response: Response):
    identifier = body.username.strip()
    password = body.password

    if not identifier or not password:
        raise HTTPException(status_code=400, detail="Username/email and password are required.")

    # Look up user credential by username or email
    user_record = identity_storage.get_user_credential_by_identifier(identifier)

    if not user_record or not verify_password(password, user_record["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email/username or password.")

    username = user_record["username"]
    email = user_record["email"]
    display_name = user_record.get("display_name", username)

    # Token Expiries
    access_expires = ACCESS_TOKEN_EXPIRE_SECONDS # 15 minutes
    refresh_expires = 30 * 24 * 3600 if body.remember_me else REFRESH_TOKEN_EXPIRE_SECONDS # 30 days vs 7 days

    access_token = create_jwt_token({"sub": username, "type": "access"}, access_expires)
    refresh_token = create_jwt_token({"sub": username, "type": "refresh"}, refresh_expires)

    # Set HTTP-Only Cookies
    response.set_cookie(
        key="jarvis_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=access_expires
    )

    if body.remember_me:
        response.set_cookie(
            key="jarvis_refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            max_age=refresh_expires
        )
    else:
        response.set_cookie(
            key="jarvis_refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax"
        )

    identity_manager.update_user_profile(display_name=display_name, email=email)

    return {
        "status": "success",
        "message": "Authenticated successfully",
        "user": {
            "username": username,
            "email": email,
            "display_name": display_name
        }
    }

@router.post("/auth/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    raise HTTPException(status_code=400, detail="Account recovery is currently unavailable.")

@router.post("/session/refresh")
def refresh_session_auth(request: Request, response: Response):
    refresh_token = request.cookies.get("jarvis_refresh_token")
    if not refresh_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header.split(" ", 1)[1]

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    payload = verify_jwt_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    username = payload.get("sub", "admin")
    user_record = identity_storage.get_user_credential_by_username(username)

    if not user_record:
        raise HTTPException(status_code=401, detail="User profile not found")

    iat = payload.get("iat", 0)
    password_updated_at = user_record.get("password_updated_at", 0)
    if password_updated_at > 0 and iat < password_updated_at:
        response.delete_cookie(key="jarvis_access_token")
        response.delete_cookie(key="jarvis_refresh_token")
        raise HTTPException(status_code=401, detail="Session revoked due to password change. Please log in again.")

    email = user_record["email"]
    display_name = user_record.get("display_name", username)

    new_access_token = create_jwt_token({"sub": username, "type": "access"}, ACCESS_TOKEN_EXPIRE_SECONDS)

    response.set_cookie(
        key="jarvis_access_token",
        value=new_access_token,
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS
    )

    return {
        "status": "success",
        "access_token": new_access_token,
        "user": {
            "username": username,
            "email": email,
            "display_name": display_name
        }
    }

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    username: Optional[str] = None

@router.patch("/auth/profile")
def update_profile(body: UpdateProfileRequest, request: Request):
    """Update display_name and/or username for the authenticated user."""
    access_token = request.cookies.get("jarvis_access_token")
    if not access_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ", 1)[1]
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    payload = verify_jwt_token(access_token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    current_username = payload.get("sub")
    if not current_username:
        raise HTTPException(status_code=401, detail="Invalid session token.")

    new_display_name = body.display_name.strip() if body.display_name else None
    if new_display_name is not None and len(new_display_name) < 1:
        raise HTTPException(status_code=400, detail="Display name cannot be empty.")
    if new_display_name is not None and len(new_display_name) > 64:
        raise HTTPException(status_code=400, detail="Display name must be 64 characters or fewer.")

    new_username = body.username.strip().lower() if body.username else None
    if new_username is not None:
        if len(new_username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
        if len(new_username) > 32:
            raise HTTPException(status_code=400, detail="Username must be 32 characters or fewer.")
        if not re.match(r"^[a-z0-9_]+$", new_username):
            raise HTTPException(status_code=400, detail="Username may only contain lowercase letters, numbers, and underscores.")

    result = identity_storage.update_user_profile_fields(
        username=current_username,
        display_name=new_display_name,
        new_username=new_username
    )

    if result is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if isinstance(result, dict) and result.get("error") == "username_taken":
        raise HTTPException(status_code=400, detail="This username is already taken.")

    return {
        "status": "success",
        "user": {
            "username": result["username"],
            "email": result["email"],
            "display_name": result.get("display_name", result["username"])
        }
    }

@router.post("/session/logout")
def logout_auth(response: Response):
    response.delete_cookie(key="jarvis_access_token")
    response.delete_cookie(key="jarvis_refresh_token")
    return {"status": "success", "message": "Logged out successfully"}
