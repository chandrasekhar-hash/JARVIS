from typing import Dict
from brain.models import PermissionLevel
from tools.logger import log_safety_confirmation

class PermissionManager:
    def __init__(self):
        self.permission_registry: Dict[str, str] = {}

    def _normalize_level(self, safety_level: str) -> str:
        s = str(safety_level).lower().strip()
        if s in ("safe", "sensitive", "read_only"):
            return PermissionLevel.SAFE
        elif s in ("confirmation_required", "ask_once", "modifying"):
            return PermissionLevel.ASK_ONCE
        elif s in ("destructive", "restricted", "always_confirm"):
            return PermissionLevel.ALWAYS_CONFIRM
        return PermissionLevel.ASK_ONCE

    def register_tool_permission(self, tool_name: str, safety_level: str) -> None:
        """Registers or updates a tool's safety level in the permission registry."""
        normalized = self._normalize_level(safety_level)
        self.permission_registry[tool_name] = normalized

    def get_permission_level(self, tool_name: str) -> str:
        """Returns the permission level for a given tool name."""
        return self.permission_registry.get(tool_name, PermissionLevel.ASK_ONCE)

    def verify_permission(self, tool_name: str, args: dict) -> str:
        """Verifies whether a tool is authorized to run."""
        safety_level = self.get_permission_level(tool_name)
        confirmed = args.get("confirmed", False)

        if safety_level == PermissionLevel.SAFE:
            return "authorized"

        elif safety_level == PermissionLevel.ASK_ONCE:
            log_safety_confirmation(tool_name, confirmed)
            if confirmed:
                return "authorized"
            return "requires_confirmation"

        elif safety_level == PermissionLevel.ALWAYS_CONFIRM:
            log_safety_confirmation(f"ALWAYS_CONFIRM::{tool_name}", confirmed)
            if confirmed:
                return "authorized"
            return "requires_restricted_approval"

        return "denied"

permission_manager = PermissionManager()
