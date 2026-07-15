from typing import Dict, Any
from tools.logger import log_safety_confirmation

class PermissionManager:
    def __init__(self):
        # Stores dynamic permissions or approvals keyed by tool name
        self.permission_registry: Dict[str, str] = {}

    def register_tool_permission(self, tool_name: str, safety_level: str):
        """Registers a tool's safety level in the permission registry."""
        self.permission_registry[tool_name] = safety_level

    def verify_permission(self, tool_name: str, args: dict) -> str:
        """
        Verifies whether a tool is authorized to run.
        Returns:
            'authorized': Permission granted, safe to execute.
            'requires_confirmation': Requires normal user confirmation.
            'requires_restricted_approval': Restricted tool requiring explicit user approval.
            'denied': Blocked.
        """
        # Fetch safety level from registry, default to 'restricted' if unregistered for max safety
        safety_level = self.permission_registry.get(tool_name, "restricted")
        confirmed = args.get("confirmed", False)
        
        if safety_level == "safe":
            return "authorized"
            
        elif safety_level == "confirmation_required":
            log_safety_confirmation(tool_name, confirmed)
            if confirmed:
                return "authorized"
            return "requires_confirmation"
            
        elif safety_level == "restricted":
            log_safety_confirmation(f"RESTRICTED::{tool_name}", confirmed)
            if confirmed:
                return "authorized"
            return "requires_restricted_approval"
            
        return "denied"

permission_manager = PermissionManager()
