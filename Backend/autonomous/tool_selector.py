import inspect
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from tools.registry import registry
from brain.permissions import permission_manager
from tools.telemetry import log_structured, backend_log
from autonomous.models import Task
from autonomous.interfaces import IToolSelector


class ToolSelectionResult(BaseModel):
    """Encapsulates the output of a tool selection evaluation."""
    selected_tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    reason: str = ""
    permission_level: str = "safe"
    is_valid: bool = True


class ToolSelector(IToolSelector):
    """Subsystem responsible for matching Task requirements with available registered desktop tools."""

    def discover_tools(self) -> List[str]:
        """Returns names of all available, platform-supported registered tools."""
        return [
            name for name, tool in registry.tools.items()
            if registry.is_supported_on_current_platform(name)
        ]

    def validate_tool_arguments(self, tool_name: str, args: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validates argument dictionary against registered tool signature parameters.
        Returns (is_valid: bool, reason: str).
        """
        if tool_name not in registry.tools:
            return False, f"Tool '{tool_name}' is not registered in ToolRegistry."

        tool = registry.tools[tool_name]
        sig = inspect.signature(tool.func)

        for param_name, param in sig.parameters.items():
            if param_name not in args and param.default is inspect.Parameter.empty:
                return False, f"Missing required parameter '{param_name}' for tool '{tool_name}'."

        return True, "Arguments validated successfully."

    async def select_tool_for_task(
        self, 
        task: Task, 
        runtime_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Selects optimal registered tool for given Task.
        Returns dictionary conforming to ToolSelectionResult schema.
        NEVER executes the tool directly.
        """
        log_structured(
            backend_log, 
            "INFO", 
            f"[ToolSelector] Evaluating tool for task '{task.name}' (Suggested: {task.suggested_tool})"
        )

        candidate_name = task.suggested_tool or ""
        args = dict(task.input_params)

        # 1. Direct suggested tool match
        if candidate_name and candidate_name in registry.tools:
            if not registry.is_supported_on_current_platform(candidate_name):
                res = ToolSelectionResult(
                    selected_tool=candidate_name,
                    arguments=args,
                    confidence=0.0,
                    reason=f"Suggested tool '{candidate_name}' is unsupported on current platform.",
                    permission_level=permission_manager.get_permission_level(candidate_name),
                    is_valid=False
                )
                return res.model_dump()

            is_valid, reason = self.validate_tool_arguments(candidate_name, args)
            perm_lvl = permission_manager.get_permission_level(candidate_name)

            res = ToolSelectionResult(
                selected_tool=candidate_name,
                arguments=args,
                confidence=0.95 if is_valid else 0.0,
                reason=reason if is_valid else f"Argument validation failed: {reason}",
                permission_level=perm_lvl,
                is_valid=is_valid
            )
            return res.model_dump()

        # 2. Heuristic capability matching based on task description keywords
        desc_lower = (task.name + " " + task.description).lower()
        matched_tool: Optional[str] = None
        matched_reason: str = ""

        if "list" in desc_lower or "scan" in desc_lower or "folder" in desc_lower:
            if "fs_list_directory" in registry.tools:
                matched_tool = "fs_list_directory"
                matched_reason = "Matched file system scanning keywords."
        elif "terminal" in desc_lower or "command" in desc_lower or "npm" in desc_lower or "pip" in desc_lower:
            if "terminal_execute" in registry.tools:
                matched_tool = "terminal_execute"
                matched_reason = "Matched command execution keywords."
        elif "browser" in desc_lower or "url" in desc_lower or "inbox" in desc_lower:
            if "browser_open_url" in registry.tools:
                matched_tool = "browser_open_url"
                matched_reason = "Matched web browsing keywords."

        if matched_tool and registry.is_supported_on_current_platform(matched_tool):
            is_valid, reason = self.validate_tool_arguments(matched_tool, args)
            perm_lvl = permission_manager.get_permission_level(matched_tool)
            res = ToolSelectionResult(
                selected_tool=matched_tool,
                arguments=args,
                confidence=0.85 if is_valid else 0.0,
                reason=matched_reason + (" " + reason if not is_valid else ""),
                permission_level=perm_lvl,
                is_valid=is_valid
            )
            return res.model_dump()

        # 3. Fallback agent reasoning pseudo-tool
        res = ToolSelectionResult(
            selected_tool="agent_reasoning",
            arguments={"query": task.description},
            confidence=0.70,
            reason="Fallback to agent reasoning engine.",
            permission_level="safe",
            is_valid=True
        )
        return res.model_dump()


tool_selector = ToolSelector()
