import inspect
from typing import Callable, List, Dict, Any, Optional


def jarvis_plugin(
    plugin_id: str,
    name: str,
    version: str = "1.0.0",
    sdk_version: str = "1.0",
    api_version: str = "1",
    minimum_runtime: str = "1.0.0",
    capabilities: Optional[List[str]] = None
):
    """
    Decorator declaring a J.A.R.V.I.S. Plugin class with manifest metadata and version constraints.
    """
    def decorator(cls):
        cls._jarvis_manifest = {
            "id": plugin_id,
            "name": name,
            "version": version,
            "sdk_version": sdk_version,
            "api_version": api_version,
            "minimum_runtime": minimum_runtime,
            "capabilities": capabilities or []
        }
        return cls
    return decorator


def jarvis_tool(name: Optional[str] = None, description: Optional[str] = None):
    """
    Decorator declaring a tool method inside a J.A.R.V.I.S. plugin, generating OpenAI-compatible JSON schema.
    """
    def decorator(func: Callable):
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__.strip() if func.__doc__ else f"Tool {tool_name}")
        sig = inspect.signature(func)

        properties = {}
        required = []

        for p_name, p in sig.parameters.items():
            if p_name in ["self", "cls"]:
                continue
            properties[p_name] = {"type": "string", "description": f"Parameter {p_name}"}
            if p.default == inspect.Parameter.empty:
                required.append(p_name)

        func._jarvis_tool_schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_desc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
        return func
    return decorator


class BaseJarvisPlugin:
    def on_install(self):
        pass

    def on_enable(self):
        pass

    def on_disable(self):
        pass

    def on_upgrade(self):
        pass

    def on_uninstall(self):
        pass
