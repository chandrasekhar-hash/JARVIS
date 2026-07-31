"""
JARVIS Product 1.8 - Opaque Secret Handle Resolver.
Resolves opaque SecretHandle references (secret_ref_...) strictly at the outbound client boundary.
"""

from typing import Dict, Any, Optional
from ..models import SecretHandle, AuthType


class SecretHandleResolver:
    def __init__(self):
        self._handles: Dict[str, SecretHandle] = {}

    def register_handle(self, handle: SecretHandle) -> None:
        self._handles[handle.secret_ref] = handle

    def get_handle(self, secret_ref: str) -> Optional[SecretHandle]:
        return self._handles.get(secret_ref)


secret_handle_resolver = SecretHandleResolver()
