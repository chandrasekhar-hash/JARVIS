"""
Product 1.4 Plugin Manifest & Dependency Validator.
"""
import os
import json
import re
from typing import Tuple, Optional, Dict, Any, List, Set
from .models import PluginManifest, PluginPermissionScope, PluginState


CURRENT_JARVIS_VERSION = "1.4.0"
SEMVER_REGEX = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9a-zA-Z.-]+))?$")
PLUGIN_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


class PluginValidator:
    """
    Validates plugin manifests, semantic versions, permissions, and resolves dependency DAGs.
    """

    @staticmethod
    def parse_semver(version_str: str) -> Tuple[bool, Optional[Tuple[int, int, int]]]:
        """Parses a SemVer 2.0 string into (major, minor, patch) tuple."""
        match = SEMVER_REGEX.match(version_str)
        if not match:
            return False, None
        try:
            major = int(match.group(1))
            minor = int(match.group(2))
            patch = int(match.group(3))
            return True, (major, minor, patch)
        except ValueError:
            return False, None

    @staticmethod
    def compare_semver(v1: str, v2: str) -> int:
        """
        Compares two SemVer strings.
        Returns:
            -1 if v1 < v2
             0 if v1 == v2
             1 if v1 > v2
        """
        ok1, parsed1 = PluginValidator.parse_semver(v1)
        ok2, parsed2 = PluginValidator.parse_semver(v2)
        if not ok1 or not ok2 or parsed1 is None or parsed2 is None:
            return 0
        if parsed1 < parsed2:
            return -1
        elif parsed1 > parsed2:
            return 1
        return 0

    @staticmethod
    def validate_manifest_dict(
        manifest_dict: Dict[str, Any],
        current_jarvis_version: str = CURRENT_JARVIS_VERSION,
    ) -> Tuple[bool, Optional[PluginManifest], Optional[str]]:
        """
        Validates a plugin manifest dictionary against schema and version constraints.
        """
        if not isinstance(manifest_dict, dict):
            return False, None, "Manifest must be a JSON object/dict."

        plugin_id = manifest_dict.get("id")
        if not plugin_id or not isinstance(plugin_id, str) or not PLUGIN_ID_REGEX.match(plugin_id):
            return False, None, f"Invalid or missing plugin 'id': {plugin_id}. Must match ^[a-zA-Z0-9_-]{{3,64}}$"

        name = manifest_dict.get("name")
        if not name or not isinstance(name, str) or len(name.strip()) < 2:
            return False, None, "Invalid or missing plugin 'name'."

        version = manifest_dict.get("version", "1.0.0")
        ok_ver, _ = PluginValidator.parse_semver(str(version))
        if not ok_ver:
            return False, None, f"Invalid plugin version format '{version}'. Must be SemVer (x.y.z)."

        min_jarvis_ver = manifest_dict.get("minimum_jarvis_version", "1.0.0")
        ok_min, _ = PluginValidator.parse_semver(str(min_jarvis_ver))
        if not ok_min:
            return False, None, f"Invalid minimum_jarvis_version format '{min_jarvis_ver}'."

        if PluginValidator.compare_semver(current_jarvis_version, min_jarvis_ver) < 0:
            return (
                False,
                None,
                f"Plugin requires JARVIS version >= {min_jarvis_ver}, but current version is {current_jarvis_version}.",
            )

        # Validate permissions
        permissions = manifest_dict.get("permissions", [])
        if not isinstance(permissions, list):
            return False, None, "'permissions' field must be a list."
        
        valid_scopes = {s.value for s in PluginPermissionScope}
        for p in permissions:
            if not isinstance(p, str) or p not in valid_scopes:
                return False, None, f"Invalid or unrecognized permission scope: '{p}'."

        # Validate entry_point
        entry_point = manifest_dict.get("entry_point", "main.py")
        if not isinstance(entry_point, str) or not entry_point.endswith(".py"):
            return False, None, f"Invalid entry_point '{entry_point}'. Must be a .py file."

        try:
            manifest = PluginManifest(**manifest_dict)
            return True, manifest, None
        except Exception as e:
            return False, None, f"Manifest instantiation error: {str(e)}"

    @staticmethod
    def validate_manifest_file(
        file_path: str,
        current_jarvis_version: str = CURRENT_JARVIS_VERSION,
    ) -> Tuple[bool, Optional[PluginManifest], Optional[str]]:
        """
        Reads and validates a plugin manifest JSON file from disk.
        """
        if not os.path.exists(file_path):
            return False, None, f"Manifest file not found: '{file_path}'"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return False, None, f"Failed to parse manifest JSON: {str(e)}"

        return PluginValidator.validate_manifest_dict(data, current_jarvis_version=current_jarvis_version)

    @staticmethod
    def resolve_dependencies_dag(
        states: List[PluginState],
    ) -> Tuple[bool, List[str], Optional[str]]:
        """
        Resolves inter-plugin dependencies using Topological Sort (Kahn's algorithm).
        Detects circular dependencies and missing prerequisites.
        Returns:
            (success, sorted_plugin_ids, error_message)
        """
        plugin_map: Dict[str, PluginState] = {s.plugin_id: s for s in states}
        in_degree: Dict[str, int] = {s.plugin_id: 0 for s in states}
        graph: Dict[str, List[str]] = {s.plugin_id: [] for s in states}

        # Build adjacency graph
        for s in states:
            for dep_id, ver_constraint in s.manifest.dependencies.items():
                if dep_id not in plugin_map:
                    return (
                        False,
                        [],
                        f"Plugin '{s.plugin_id}' requires missing dependency '{dep_id}'.",
                    )

                # Check version compatibility if specified
                dep_plugin = plugin_map[dep_id]
                if ver_constraint.startswith("^"):
                    target_ver = ver_constraint[1:]
                    if PluginValidator.compare_semver(dep_plugin.manifest.version, target_ver) < 0:
                        return (
                            False,
                            [],
                            f"Plugin '{s.plugin_id}' requires '{dep_id}' >= {target_ver}, but found {dep_plugin.manifest.version}.",
                        )

                graph[dep_id].append(s.plugin_id)
                in_degree[s.plugin_id] += 1

        # Kahn's Algorithm
        queue: List[str] = [p_id for p_id, deg in in_degree.items() if deg == 0]
        sorted_order: List[str] = []

        while queue:
            curr = queue.pop(0)
            sorted_order.append(curr)

            for neighbor in graph[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_order) != len(states):
            return False, [], "Circular dependency detected among installed plugins."

        return True, sorted_order, None
