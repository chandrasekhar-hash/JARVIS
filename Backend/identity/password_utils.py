import os
import hashlib
import binascii

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return binascii.hexlify(salt).decode('ascii') + ":" + binascii.hexlify(pwd_hash).decode('ascii')

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a password against a stored PBKDF2 hash."""
    if not stored_hash or ":" not in stored_hash:
        return False
    salt_hex, hash_hex = stored_hash.split(":", 1)
    try:
        salt = binascii.unhexlify(salt_hex)
        expected_hash = binascii.unhexlify(hash_hex)
        actual_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000) == expected_hash
    except Exception:
        return False
