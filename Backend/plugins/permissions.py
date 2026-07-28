import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger("JARVIS_PermissionEngine")

# Standard Capability List
ALLOWED_CAPABILITIES = {
    "fs:read",
    "fs:write",
    "net:outbound",
    "system:exec",
    "speech:tts",
    "speech:stt",
    "vision:screen",
    "memory:read",
    "memory:write",
    "tasks:manage"
}


class PermissionEngine:
    """
    Capability Permission Engine validating requested plugin capabilities
    against allowed system policies and granted permissions.
    """

    def __init__(self):
        # plugin_id -> Set[str] granted capabilities
        self.granted_permissions: Dict[str, Set[str]] = {}

    def grant_permissions(self, plugin_id: str, capabilities: List[str]):
        granted = {c for c in capabilities if c in ALLOWED_CAPABILITIES or c.startswith("custom:")}
        self.granted_permissions[plugin_id] = granted
        logger.info(f"Granted permissions for plugin '{plugin_id}': {granted}")

    def revoke_permissions(self, plugin_id: str):
        if plugin_id in self.granted_permissions:
            del self.granted_permissions[plugin_id]
            logger.info(f"Revoked permissions for plugin '{plugin_id}'")

    def check_permission(self, plugin_id: str, required_capability: str) -> bool:
        granted = self.granted_permissions.get(plugin_id, set())
        if "all" in granted or required_capability in granted:
            return True
        logger.warning(f"Permission DENIED for plugin '{plugin_id}': Missing capability '{required_capability}'")
        return False


permission_engine = PermissionEngine()
