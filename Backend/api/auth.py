import re
import time
import logging
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional

from identity.identity_manager import identity_manager
from identity.identity_storage import identity_storage
from identity.password_utils import hash_password, verify_password
from identity.email_service import email_service
from identity.otp_service import otp_service
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

class RequestOtpRequest(BaseModel):
    username: str
    email: str

class VerifyOtpRequest(BaseModel):
    email: str
    otp: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    verification_token: str
    display_name: Optional[str] = None

class LoginRequest(BaseModel):
    username: str  # Carries Username or Email
    password: str
    remember_me: Optional[bool] = False

class ForgotPasswordRequest(BaseModel):
    email: str

@router.post("/auth/register/request-otp")
def request_registration_otp(body: RequestOtpRequest):
    clean_username = body.username.strip()
    clean_email = body.email.strip().lower()

    if not clean_username:
        raise HTTPException(status_code=400, detail="Username is required.")

    if not clean_email or not EMAIL_REGEX.match(clean_email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")

    # Duplicate username check
    if identity_storage.get_user_credential_by_username(clean_username):
        raise HTTPException(status_code=400, detail="This username is already taken.")

    # Duplicate email check
    if identity_storage.get_user_credential_by_email(clean_email):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # Generate cryptographically secure OTP
    otp, err = otp_service.generate_registration_otp(clean_email)
    if err:
        raise HTTPException(status_code=400, detail=err)

    # Send OTP via Brevo API
    try:
        email_service.send_registration_otp(clean_email, otp)
    except Exception as e:
        logger.error(f"[Auth] Failed to send registration OTP to {clean_email}: {e}")
        raise HTTPException(status_code=500, detail="Unable to send verification code. Please try again.")

    return {
        "status": "pending_verification",
        "message": f"Verification code sent successfully to {clean_email}."
    }

@router.post("/auth/register/verify-otp")
def verify_registration_otp(body: VerifyOtpRequest):
    clean_email = body.email.strip().lower()
    clean_otp = body.otp.strip()

    if not clean_email or not clean_otp:
        raise HTTPException(status_code=400, detail="Email and verification code are required.")

    success, token, err = otp_service.verify_registration_otp(clean_email, clean_otp)
    if not success or not token:
        raise HTTPException(status_code=400, detail=err or "Invalid verification code.")

    return {
        "status": "success",
        "message": "Email verified.",
        "verification_token": token
    }

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

    # 3. Password requirements validation
    if len(password) < 8 or not re.search(r"[A-Z]", password) or not SPECIAL_CHAR_REGEX.search(password):
        raise HTTPException(status_code=400, detail="Password does not meet the security requirements.")

    # 4. Verify token
    if not body.verification_token or not otp_service.consume_verification_token(body.verification_token, clean_email):
        raise HTTPException(status_code=400, detail="Email verification has expired or is invalid. Please verify your email again.")

    # 5. Duplicate username check
    if identity_storage.get_user_credential_by_username(clean_username):
        raise HTTPException(status_code=400, detail="This username is already taken.")

    # 6. Duplicate email check
    if identity_storage.get_user_credential_by_email(clean_email):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # 7. Secure Password Hashing (PBKDF2-HMAC-SHA256)
    hashed_pwd = hash_password(password)

    # 8. Save user credential with is_verified=1
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

class ForgotPasswordRequestOtpRequest(BaseModel):
    identifier: str

class ForgotPasswordVerifyOtpRequest(BaseModel):
    identifier: str
    otp: str

class ForgotPasswordResetPasswordRequest(BaseModel):
    identifier: str
    reset_token: str
    new_password: str

@router.post("/auth/forgot-password/request-otp")
def forgot_password_request_otp(body: ForgotPasswordRequestOtpRequest):
    clean_id = body.identifier.strip().lower()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Please enter your email or username.")

    # Locate account by username or email
    user = identity_storage.get_user_credential_by_identifier(clean_id)

    # ANTI-ENUMERATION: Return generic message if user not found, without exposing account non-existence
    if not user or not user.get("email"):
        return {
            "status": "pending_verification",
            "message": "If an account exists, a verification code has been sent."
        }

    target_email = user["email"].strip().lower()

    # Generate cryptographically secure OTP for password reset
    otp, err = otp_service.generate_password_reset_otp(target_email)
    if err:
        raise HTTPException(status_code=400, detail=err)

    # Dispatch OTP to the user's actual registered email address using Brevo API
    try:
        email_service.send_password_reset_otp(target_email, otp)
    except Exception as e:
        logger.error(f"[Auth] Failed to send password reset OTP to {target_email}: {e}")
        raise HTTPException(status_code=500, detail="Unable to send verification code. Please try again.")

    return {
        "status": "pending_verification",
        "message": "If an account exists, a verification code has been sent."
    }

@router.post("/auth/forgot-password/verify-otp")
def forgot_password_verify_otp(body: ForgotPasswordVerifyOtpRequest):
    clean_id = body.identifier.strip().lower()
    clean_otp = body.otp.strip()

    if not clean_id or not clean_otp:
        raise HTTPException(status_code=400, detail="Identifier and verification code are required.")

    user = identity_storage.get_user_credential_by_identifier(clean_id)
    if not user or not user.get("email"):
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    target_email = user["email"].strip().lower()

    success, reset_token, err = otp_service.verify_password_reset_otp(target_email, clean_otp)
    if not success or not reset_token:
        raise HTTPException(status_code=400, detail=err or "Invalid verification code.")

    return {
        "status": "success",
        "message": "Identity verified.",
        "reset_token": reset_token
    }

@router.post("/auth/forgot-password/reset-password")
def forgot_password_reset_password(body: ForgotPasswordResetPasswordRequest):
    clean_id = body.identifier.strip().lower()
    new_password = body.new_password

    if not clean_id or not body.reset_token or not new_password:
        raise HTTPException(status_code=400, detail="All fields are required.")

    if len(new_password) < 8 or not re.search(r"[A-Z]", new_password) or not SPECIAL_CHAR_REGEX.search(new_password):
        raise HTTPException(status_code=400, detail="Password does not meet the security requirements.")

    user = identity_storage.get_user_credential_by_identifier(clean_id)
    if not user or not user.get("email"):
        raise HTTPException(status_code=400, detail="Unable to reset password.")

    target_email = user["email"].strip().lower()

    # Consume single-use reset token
    if not otp_service.consume_password_reset_token(body.reset_token, target_email):
        raise HTTPException(status_code=400, detail="Password reset token is invalid or has expired. Please verify your identity again.")

    # Hash new password
    hashed_pwd = hash_password(new_password)

    # Update user password in database
    updated = identity_storage.update_user_password(target_email, hashed_pwd)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update password.")

    # Invalidate all existing sessions and refresh tokens for this user
    identity_storage.revoke_all_user_sessions(target_email)

    return {
        "status": "success",
        "message": "Your password has been updated successfully. Please log in."
    }

@router.post("/session/refresh")
async def refresh_session_auth(request: Request, response: Response):
    refresh_token = request.cookies.get("jarvis_refresh_token")
    if not refresh_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header.split(" ", 1)[1]

    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except Exception:
            pass

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    # Local session_manager fallback for local tokens (rtk_...)
    if refresh_token.startswith("rtk_") or refresh_token.startswith("sess_"):
        from identity.session_manager import session_manager
        success, token_pair, err = session_manager.refresh_session(refresh_token)
        if not success or not token_pair:
            raise HTTPException(status_code=401, detail=err or "Token refresh failed")
        return {"status": "success", "token_pair": token_pair.model_dump()}

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

class DeleteAccountRequest(BaseModel):
    password: str

@router.post("/account/delete")
@router.delete("/account/delete")
@router.post("/auth/delete-account")
@router.delete("/auth/delete-account")
@router.post("/auth/account")
@router.delete("/auth/account")
@router.post("/account")
@router.delete("/account")
def delete_account(body: DeleteAccountRequest, request: Request, response: Response):
    """
    Permanently deletes the authenticated user's account, profile, sessions, and data.
    Requires password re-verification.
    """
    access_token = request.cookies.get("jarvis_access_token")
    if not access_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ", 1)[1]
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated. Session missing.")

    payload = verify_jwt_token(access_token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")

    current_username = payload.get("sub")
    if not current_username:
        raise HTTPException(status_code=401, detail="Invalid session payload.")

    # Robust user credential lookup by identifier, username, email, or profile
    user_record = identity_storage.get_user_credential_by_identifier(current_username)
    if not user_record:
        user_record = identity_storage.get_user_credential_by_username(current_username)
    if not user_record:
        user_record = identity_storage.get_user_credential_by_email(current_username)

    if not user_record:
        try:
            local_prof = identity_manager.get_user_profile()
            if local_prof and local_prof.email:
                user_record = identity_storage.get_user_credential_by_email(local_prof.email)
        except Exception:
            pass

    # Fallback: if single user exists in user_credentials table
    if not user_record:
        try:
            with identity_storage._get_connection() as conn:
                rows = conn.execute("SELECT * FROM user_credentials").fetchall()
                if len(rows) == 1:
                    user_record = dict(rows[0])
        except Exception:
            pass

    if not user_record:
        raise HTTPException(status_code=400, detail="Account record not found. Please log in again.")

    provided_password = body.password
    if not provided_password or not verify_password(provided_password, user_record["password_hash"]):
        raise HTTPException(status_code=400, detail="Incorrect password.")

    user_email = user_record["email"]
    username = user_record["username"]

    # Revoke sessions & remove credentials and user profiles
    identity_storage.revoke_all_user_sessions(user_email)
    identity_storage.revoke_all_user_sessions(username)
    identity_storage.delete_user_credential_by_username(username)
    identity_storage.delete_user_credential_by_email(user_email)

    # Clear HTTP cookies
    response.delete_cookie(key="jarvis_access_token")
    response.delete_cookie(key="jarvis_refresh_token")

    logger.info(f"[Auth] Permanently deleted account for user '{username}' ({user_email})")

    return {
        "status": "success",
        "message": "Account permanently deleted."
    }

@router.post("/session/logout")
def logout_auth(response: Response):
    response.delete_cookie(key="jarvis_access_token")
    response.delete_cookie(key="jarvis_refresh_token")
    return {"status": "success", "message": "Logged out successfully"}
