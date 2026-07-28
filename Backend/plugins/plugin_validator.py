import os
import json
from typing import Tuple, Optional, List
from plugins.plugin_models import PluginManifest, PluginPermissionEnum
from tools.telemetry import log_structured, backend_log

ALLOWED_PERMISSIONS = {p.value for p in PluginPermissionEnum}

class PluginValidator:
    """
    Validates local plugin manifests (plugin.json) for structural compliance,
    permission declarations, version compatibility, and entrypoint existence.
    """

    @staticmethod
    def validate_manifest_file(manifest_path: str) -> Tuple[bool, Optional[PluginManifest], Optional[str]]:
        if not os.path.exists(manifest_path):
            return False, None, f"Manifest file not found: {manifest_path}"
            
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return False, None, f"Invalid JSON syntax in manifest: {str(e)}"

        return PluginValidator.validate_manifest_dict(data, os.path.dirname(manifest_path))

    @staticmethod
    def validate_manifest_dict(data: dict, plugin_dir: str) -> Tuple[bool, Optional[PluginManifest], Optional[str]]:
        required_fields = ["id", "name", "description"]
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return False, None, f"Manifest missing required field: '{field}'"

        plugin_id = str(data["id"]).strip()
        if not plugin_id.isidentifier() and not all(c.isalnum() or c in "_-" for c in plugin_id):
            return False, None, f"Invalid plugin ID syntax: '{plugin_id}'. Must be alphanumeric with underscores/hyphens."

        # Validate permissions
        permissions = data.get("permissions", [])
        if not isinstance(permissions, list):
            return False, None, "Permissions must be a list of strings."

        invalid_perms = [p for p in permissions if p not in ALLOWED_PERMISSIONS]
        if invalid_perms:
            log_structured(
                backend_log,
                "WARNING",
                f"[PluginValidator] Plugin '{plugin_id}' requested unknown permissions: {invalid_perms}"
            )

        # Validate entrypoint file existence
        entry_file = data.get("entry", "main.py")
        entry_path = os.path.join(plugin_dir, entry_file)
        if not os.path.exists(entry_path):
            return False, None, f"Plugin entry point file '{entry_file}' not found in directory: {plugin_dir}"

        try:
            manifest = PluginManifest(**data)
            return True, manifest, None
        except Exception as e:
            return False, None, f"Manifest schema validation error: {str(e)}"

validator = PluginValidator()
