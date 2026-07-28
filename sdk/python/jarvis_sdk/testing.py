import json
from typing import Dict, Any, Type
from jarvis_sdk.plugin import BaseJarvisPlugin


class PluginTestHarness:
    """
    Developer Plugin Test Harness for local verification of third-party plugins.
    """

    def __init__(self, plugin_cls: Type[BaseJarvisPlugin]):
        self.plugin_cls = plugin_cls
        self.instance = plugin_cls()

    def get_manifest(self) -> Dict[str, Any]:
        return getattr(self.plugin_cls, "_jarvis_manifest", {})

    def get_registered_tools(self) -> Dict[str, Dict[str, Any]]:
        tools = {}
        for attr_name in dir(self.instance):
            attr = getattr(self.instance, attr_name)
            if callable(attr) and hasattr(attr, "_jarvis_tool_schema"):
                schema = getattr(attr, "_jarvis_tool_schema")
                tools[schema["function"]["name"]] = schema
        return tools

    def invoke_tool(self, tool_name: str, **kwargs) -> Any:
        for attr_name in dir(self.instance):
            attr = getattr(self.instance, attr_name)
            if callable(attr) and hasattr(attr, "_jarvis_tool_schema"):
                schema = getattr(attr, "_jarvis_tool_schema")
                if schema["function"]["name"] == tool_name:
                    return attr(**kwargs)
        raise ValueError(f"Tool '{tool_name}' not found on plugin instance.")
