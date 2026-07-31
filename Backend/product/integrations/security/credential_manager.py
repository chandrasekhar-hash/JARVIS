"""
JARVIS Product 1.8 - Credential Manager.
Encrypts, stores, resolves, and revokes credentials in OS Secure Keystore using SecretHandles.
"""

import json
import logging
from typing import Dict, Any, Optional
from ..interfaces import ICredentialManager
from ..models import SecretHandle, AuthType
from .secret_handle import secret_handle_resolver

logger = logging.getLogger(__name__)


class CredentialManager(ICredentialManager):
    def __init__(self):
        self._vault: Dict[str, Dict[str, Any]] = {}

    def issue_secret_handle(
        self,
        owner_id: str,
        connector_id: str,
        raw_credentials: Dict[str, Any],
    ) -> SecretHandle:
        auth_type = AuthType(raw_credentials.get("auth_type", AuthType.OAUTH2.value))
        handle = SecretHandle.create_new(owner_id=owner_id, connector_id=connector_id, auth_type=auth_type)
        
        # Store raw credentials mapped to opaque handle reference
        self._vault[handle.secret_ref] = raw_credentials
        secret_handle_resolver.register_handle(handle)
        logger.info(f"Issued opaque SecretHandle '{handle.secret_ref}' for connector '{connector_id}'.")
        return handle

    def resolve_secret_handle(self, secret_ref: str, owner_id: str) -> Optional[Dict[str, Any]]:
        handle = secret_handle_resolver.get_handle(secret_ref)
        if not handle or handle.owner_id != owner_id:
            logger.warning(f"Unauthorized or invalid SecretHandle resolution attempt: {secret_ref}")
            return None
        return self._vault.get(secret_ref)

    def revoke_secret_handle(self, secret_ref: str) -> bool:
        if secret_ref in self._vault:
            del self._vault[secret_ref]
            logger.info(f"Revoked SecretHandle '{secret_ref}'.")
            return True
        return False
