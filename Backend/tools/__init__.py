# Tools package exports
import sys

def __getattr__(name: str):
    """Dynamic resolution of legacy tools imports to brain components."""
    legacy_brain_map = {
        "permission_manager": ("brain.permissions", "permission_manager"),
        "PermissionManager": ("brain.permissions", "PermissionManager"),
        "desktop_context": ("brain.context", "desktop_context"),
        "DesktopContextManager": ("brain.context", "DesktopContextManager"),
        "reference_resolver": ("brain.conversation", "reference_resolver"),
        "ReferenceResolver": ("brain.conversation", "ReferenceResolver"),
        "tool_planner": ("brain.planner", "tool_planner"),
        "ToolPlanner": ("brain.planner", "ToolPlanner"),
        "task_manager": ("brain.task_manager", "task_manager"),
        "TaskManager": ("brain.task_manager", "TaskManager"),
        "execution_manager": ("brain.executor", "execution_manager"),
        "ExecutionManager": ("brain.executor", "ExecutionManager"),
        "desktop_action_engine": ("brain.action_engine", "desktop_action_engine"),
        "DesktopActionEngine": ("brain.action_engine", "DesktopActionEngine"),
        "event_bus": ("brain.event_bus", "event_bus"),
        "EventBus": ("brain.event_bus", "EventBus"),
    }
    if name in legacy_brain_map:
        mod_name, attr_name = legacy_brain_map[name]
        mod = __import__(mod_name, fromlist=[attr_name])
        return getattr(mod, attr_name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
