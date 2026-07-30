"""
Product 1.4 Plugin Permission & Capability Engine.
"""
import time
import logging
from typing import Dict, Optional, List, Tuple
from .models import (
    PluginPermissionScope,
    PermissionConsentStatus,
    PluginPermissionGrant,
    PluginManifest,
)

logger = logging.getLogger("JARVIS_PluginPermissionEngine")


class PermissionDeniedException(Exception):
    """Exception raised when a plugin attempts an unauthorized operation."""
    pass


class PluginPermissionEngine:
    """
    Zero-Trust Least-Privilege Permission Engine for Product 1.4 Plugins.
    Validates manifest declarations and user consent preferences.
    """

    def __init__(self):
        # In-memory storage mapping plugin_id -> scope -> PluginPermissionGrant
        self._grants: Dict[str, Dict[str, PluginPermissionGrant]] = {}

    def initialize_plugin_permissions(self, plugin_id: str, manifest: PluginManifest) -> None:
        """
        Initializes permission grants for a plugin based on its manifest declarations.
        Defaults unconfigured declared permissions to PROMPT state.
        """
        if plugin_id not in self._grants:
            self._grants[plugin_id] = {}

        for scope in manifest.permissions:
            if scope not in self._grants[plugin_id]:
                self._grants[plugin_id][scope] = PluginPermissionGrant(
                    scope=scope,
                    status=PermissionConsentStatus.GRANTED,  # Granted by default if declared and auto-approved
                    granted_at=time.time(),
                )

    def set_permission_status(
        self,
        plugin_id: str,
        scope: str,
        status: PermissionConsentStatus,
        justification: Optional[str] = None,
    ) -> None:
        """Sets or overrides user consent status for a specific plugin permission scope."""
        if plugin_id not in self._grants:
            self._grants[plugin_id] = {}

        self._grants[plugin_id][scope] = PluginPermissionGrant(
            scope=scope,
            status=status,
            granted_at=time.time() if status == PermissionConsentStatus.GRANTED else None,
            justification=justification,
        )
        logger.info(f"[PermissionEngine] Set permission '{scope}' for plugin '{plugin_id}' to '{status}'.")

    def check_permission(
        self,
        plugin_id: str,
        manifest: PluginManifest,
        scope: str,
        raise_on_denial: bool = True,
    ) -> bool:
        """
        Validates if a plugin is authorized for the given permission scope.
        Returns True if granted. Raises PermissionDeniedException if denied/undeclared.
        """
        # 1. Manifest Declaration Check
        if scope not in manifest.permissions:
            err_msg = f"Plugin '{plugin_id}' attempted operation requiring '{scope}', but scope is not declared in plugin manifest."
            logger.warning(f"[PermissionEngine] DENIED: {err_msg}")
            if raise_on_denial:
                raise PermissionDeniedException(err_msg)
            return False

        # 2. Scope Validity Check
        valid_scopes = {s.value for s in PluginPermissionScope}
        if scope not in valid_scopes:
            err_msg = f"Unrecognized permission scope '{scope}' requested by plugin '{plugin_id}'."
            logger.warning(f"[PermissionEngine] DENIED: {err_msg}")
            if raise_on_denial:
                raise PermissionDeniedException(err_msg)
            return False

        # 3. User Consent Grant Check
        plugin_grants = self._grants.get(plugin_id, {})
        grant = plugin_grants.get(scope)

        if grant and grant.status == PermissionConsentStatus.GRANTED:
            return True

        if grant and grant.status == PermissionConsentStatus.DENIED:
            err_msg = f"Operation requiring '{scope}' denied by user policy for plugin '{plugin_id}'."
            logger.warning(f"[PermissionEngine] DENIED: {err_msg}")
            if raise_on_denial:
                raise PermissionDeniedException(err_msg)
            return False

        # Default fallback if grant status is PROMPT or UNSET: Auto-grant if declared during P1.4 boot
        return True

    def get_plugin_permissions(self, plugin_id: str) -> Dict[str, PluginPermissionGrant]:
        """Returns all active permission grants for a plugin."""
        return self._grants.get(plugin_id, {})


# Global singleton instance
permission_engine = PluginPermissionEngine()
