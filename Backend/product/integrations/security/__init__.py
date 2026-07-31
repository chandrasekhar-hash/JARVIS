"""
JARVIS Product 1.8 - Security Subsystem Initialization.
"""

from .secret_handle import SecretHandleResolver, secret_handle_resolver
from .credential_manager import CredentialManager
from .oauth_manager import OAuthManager

__all__ = [
    "SecretHandleResolver",
    "secret_handle_resolver",
    "CredentialManager",
    "OAuthManager",
]
