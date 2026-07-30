"""
Product 1.5 Execution Permission Gateway.
"""
import sys
import logging
from typing import Dict, Any, Optional, Tuple
from .models import ToolMetadata, ExecutionContext
from brain.permissions import permission_manager

logger = logging.getLogger("JARVIS_ExecutionPermissionGateway")


class ExecutionPermissionDeniedException(Exception):
    """Exception raised when execution permission is denied."""
    pass


class ExecutionPermissionGateway:
    """
    Multi-tiered Execution Permission Gateway bridging P1.1 Identity Security,
    P1.4 Plugin Capabilities, and Safety Level Authorization.
    """

    def __init__(self, plugin_permission_engine: Optional[Any] = None, audit_logger: Optional[Any] = None):
        self.plugin_permission_engine = plugin_permission_engine
        self.audit_logger = audit_logger

    def get_current_platform(self) -> str:
        """Determines host operating system platform."""
        plat = sys.platform
        if plat == "win32":
            return "windows"
        elif plat == "darwin":
            return "macos"
        elif plat.startswith("linux"):
            return "linux"
        return "unknown"

    def is_platform_supported(self, metadata: ToolMetadata) -> bool:
        """Verifies if host operating system is supported by tool metadata."""
        current = self.get_current_platform()
        supported = [p.lower() for p in metadata.supported_platforms]
        return current in supported or "all" in supported or "any" in supported

    def authorize_execution(
        self,
        metadata: ToolMetadata,
        context: ExecutionContext,
        kwargs: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates authorization across platform, safety levels, identity security context,
        and plugin capability grants.
        """
        # 1. Platform Check
        if not self.is_platform_supported(metadata):
            current_plat = self.get_current_platform()
            err = f"Tool '{metadata.tool_id}' is not supported on platform '{current_plat}'."
            logger.warning(f"[PermissionGateway] DENIED: {err}")
            return False, err

        # 2. Tool Safety Level & User Confirmation Check
        safety = metadata.safety_level.lower()
        confirmed = kwargs.get("confirmed", False)

        if safety == "confirmation_required" and not confirmed:
            err = f"Tool '{metadata.tool_id}' requires user confirmation before execution."
            logger.warning(f"[PermissionGateway] CONFIRMATION_REQUIRED: {err}")
            return False, err

        if safety == "restricted":
            # Check user role from security_context if present
            if context.security_context and hasattr(context.security_context, "role"):
                user_role = str(context.security_context.role).lower()
                if "admin" not in user_role and not confirmed:
                    err = f"Tool '{metadata.tool_id}' is restricted and requires administrator role or explicit approval."
                    logger.warning(f"[PermissionGateway] DENIED: {err}")
                    return False, err

        # 3. P1.4 Plugin Capability Verification (if plugin tool or plugin caller)
        if metadata.source == "plugin" and metadata.owner != "core":
            if self.plugin_permission_engine is not None:
                manifest_ref = getattr(context, "plugin_reference", None)
                if manifest_ref and hasattr(manifest_ref, "manifest"):
                    for cap in metadata.capabilities:
                        try:
                            # Map capability token (e.g. filesystem:read -> filesystem.read)
                            scope_id = cap.replace(":", ".")
                            self.plugin_permission_engine.check_permission(
                                plugin_id=metadata.owner,
                                manifest=manifest_ref.manifest,
                                scope=scope_id,
                                raise_on_denial=True,
                            )
                        except Exception as e:
                            err = f"Plugin '{metadata.owner}' permission check failed for scope '{cap}': {str(e)}"
                            logger.warning(f"[PermissionGateway] DENIED: {err}")
                            return False, err

        # 4. Log audit event if logger present
        if self.audit_logger is not None and hasattr(self.audit_logger, "log"):
            try:
                self.audit_logger.log(
                    event="TOOL_EXECUTION_AUTHORIZED",
                    user_id=context.user_id,
                    tool_id=metadata.tool_id,
                    correlation_id=context.correlation_id,
                )
            except Exception as e:
                logger.warning(f"[PermissionGateway] Audit log failed: {e}")

        return True, None


# Global singleton instance
permission_gateway_instance = ExecutionPermissionGateway()
