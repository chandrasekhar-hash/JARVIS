"""
Product 1.5 Tool Metadata Registry and Schema Validator.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from .models import ToolMetadata, ToolCategory

logger = logging.getLogger("JARVIS_ToolMetadataRegistry")


class SchemaValidationError(Exception):
    """Exception raised when arguments or output fail JSON Schema validation."""
    pass


class ToolMetadataRegistry:
    """
    Registry managing declarative ToolMetadata schemas for core system tools and plugin skills.
    Includes argument type validation and schema verification.
    """

    def __init__(self, core_registry: Optional[Any] = None, skills_registry: Optional[Any] = None):
        self._tools: Dict[str, ToolMetadata] = {}
        self.core_registry = core_registry
        self.skills_registry = skills_registry

    def register_tool_metadata(self, metadata: ToolMetadata) -> bool:
        """Registers a tool metadata object in the registry."""
        self._tools[metadata.tool_id] = metadata
        logger.info(f"[MetadataRegistry] Registered metadata for tool '{metadata.tool_id}'.")
        return True

    def get_tool_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        """
        Retrieves metadata for a tool ID.
        If not found in local map, checks core tool registry or P1.4 skills registry and auto-converts.
        """
        if tool_id in self._tools:
            return self._tools[tool_id]

        # Dynamic fallback to core registry
        if self.core_registry is not None and hasattr(self.core_registry, "tools"):
            core_tool = self.core_registry.tools.get(tool_id)
            if core_tool is not None:
                meta = ToolMetadata(
                    tool_id=tool_id,
                    name=core_tool.name,
                    description=core_tool.description,
                    safety_level=core_tool.safety_level,
                    supported_platforms=core_tool.supported_platforms,
                    input_schema=core_tool.parameters,
                    handler=core_tool.func,
                    source="built_in",
                )
                self._tools[tool_id] = meta
                return meta

        # Dynamic fallback to skills registry
        if self.skills_registry is not None and hasattr(self.skills_registry, "get_skill"):
            skill = self.skills_registry.get_skill(tool_id)
            if skill is not None:
                meta = ToolMetadata(
                    tool_id=skill.skill_id,
                    name=skill.name,
                    description=skill.description,
                    category=ToolCategory.PLUGIN,
                    input_schema=skill.parameters_schema,
                    handler=skill.handler,
                    owner=skill.plugin_id,
                    source="plugin",
                )
                self._tools[tool_id] = meta
                return meta

        return None

    def unregister_tool_metadata(self, tool_id: str) -> bool:
        """Unregisters tool metadata."""
        if tool_id in self._tools:
            del self._tools[tool_id]
            return True
        return False

    def list_all_metadata(self) -> List[ToolMetadata]:
        """Returns all registered tool metadata."""
        return list(self._tools.values())

    def validate_input(self, metadata: ToolMetadata, kwargs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates keyword arguments against tool's input_schema.
        """
        schema = metadata.input_schema
        if not schema or not isinstance(schema, dict):
            return True, None

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Check required fields
        for req_field in required:
            if req_field not in kwargs or kwargs[req_field] is None:
                err = f"Missing required parameter '{req_field}' for tool '{metadata.tool_id}'."
                return False, err

        # Check property types
        for param_name, param_val in kwargs.items():
            if param_name in properties:
                expected = properties[param_name]
                exp_type = expected.get("type") if isinstance(expected, dict) else None

                if exp_type == "string" and not isinstance(param_val, str):
                    return False, f"Parameter '{param_name}' expects string, got {type(param_val).__name__}."
                elif exp_type in ("integer", "number") and not isinstance(param_val, (int, float)):
                    return False, f"Parameter '{param_name}' expects numeric, got {type(param_val).__name__}."
                elif exp_type == "boolean" and not isinstance(param_val, bool):
                    return False, f"Parameter '{param_name}' expects boolean, got {type(param_val).__name__}."
                elif exp_type == "array" and not isinstance(param_val, list):
                    return False, f"Parameter '{param_name}' expects array/list, got {type(param_val).__name__}."
                elif exp_type == "object" and not isinstance(param_val, dict):
                    return False, f"Parameter '{param_name}' expects object/dict, got {type(param_val).__name__}."

        return True, None

    def validate_output(self, metadata: ToolMetadata, output_payload: Any) -> Tuple[bool, Optional[str]]:
        """
        Validates tool output payload against output_schema if specified.
        """
        schema = metadata.output_schema
        if not schema or not isinstance(schema, dict):
            return True, None

        exp_type = schema.get("type")
        if exp_type == "string" and not isinstance(output_payload, str):
            return False, f"Output expects string, got {type(output_payload).__name__}."
        elif exp_type == "object" and not isinstance(output_payload, dict):
            return False, f"Output expects dictionary, got {type(output_payload).__name__}."
        elif exp_type == "array" and not isinstance(output_payload, list):
            return False, f"Output expects list, got {type(output_payload).__name__}."

        return True, None


# Global singleton instance
metadata_registry_instance = ToolMetadataRegistry()
