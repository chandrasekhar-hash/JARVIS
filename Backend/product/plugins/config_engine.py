"""
Product 1.4 Plugin Configuration Engine (P1.3 Integration Bridge).
"""
import logging
from typing import Dict, Any, Optional
from .models import PluginManifest

logger = logging.getLogger("JARVIS_PluginConfigEngine")


class PluginConfigEngine:
    """
    Bridge providing namespaced, schema-validated configuration storage for Product 1.4 Plugins.
    Interoperates with P1.3 PreferenceManager while maintaining fallback in-memory state.
    """

    def __init__(self, preference_manager: Optional[Any] = None):
        self.preference_manager = preference_manager
        self._local_config_store: Dict[str, Dict[str, Any]] = {}

    def get_setting(
        self,
        plugin_id: str,
        manifest: PluginManifest,
        key: str,
        default: Any = None,
        user_id: str = "default_user",
    ) -> Any:
        """
        Retrieves a namespaced configuration setting for a plugin.
        Order of Precedence:
          1. User override in P1.3 PreferenceManager / storage
          2. Plugin local runtime config override
          3. Default specified in manifest configuration_schema
          4. Caller default fallback
        """
        namespaced_key = f"plugin.{plugin_id}.{key}"

        # 1. Check P1.3 PreferenceManager if available
        if self.preference_manager is not None:
            try:
                prefs = self.preference_manager.get_preferences(user_id)
                if prefs and hasattr(prefs, "custom_settings"):
                    if namespaced_key in prefs.custom_settings:
                        return prefs.custom_settings[namespaced_key]
            except Exception as e:
                logger.warning(f"[PluginConfigEngine] P1.3 read warning for '{namespaced_key}': {e}")

        # 2. Check local plugin config store
        plugin_store = self._local_config_store.get(plugin_id, {})
        if key in plugin_store:
            return plugin_store[key]

        # 3. Check manifest schema default
        schema = manifest.configuration_schema
        if key in schema and isinstance(schema[key], dict) and "default" in schema[key]:
            return schema[key]["default"]

        # 4. Fallback caller default
        return default

    def set_setting(
        self,
        plugin_id: str,
        manifest: PluginManifest,
        key: str,
        value: Any,
        user_id: str = "default_user",
    ) -> bool:
        """
        Validates and updates a namespaced configuration setting for a plugin.
        """
        # Type validation if defined in schema
        schema = manifest.configuration_schema
        if key in schema and isinstance(schema[key], dict):
            expected_type = schema[key].get("type")
            if expected_type:
                if expected_type == "string" and not isinstance(value, str):
                    raise ValueError(f"Setting '{key}' expects string, got {type(value).__name__}")
                elif expected_type in ("integer", "number") and not isinstance(value, (int, float)):
                    raise ValueError(f"Setting '{key}' expects numeric, got {type(value).__name__}")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    raise ValueError(f"Setting '{key}' expects boolean, got {type(value).__name__}")

        # Save to local store
        if plugin_id not in self._local_config_store:
            self._local_config_store[plugin_id] = {}
        self._local_config_store[plugin_id][key] = value

        # Save to P1.3 PreferenceManager if available
        namespaced_key = f"plugin.{plugin_id}.{key}"
        if self.preference_manager is not None:
            try:
                prefs = self.preference_manager.get_preferences(user_id)
                if prefs and hasattr(prefs, "custom_settings"):
                    prefs.custom_settings[namespaced_key] = value
                    self.preference_manager.update_preferences(user_id, prefs)
            except Exception as e:
                logger.warning(f"[PluginConfigEngine] P1.3 write warning for '{namespaced_key}': {e}")

        logger.info(f"[PluginConfigEngine] Updated setting '{key}' = {value} for plugin '{plugin_id}'")
        return True


# Global singleton instance
config_engine_instance = PluginConfigEngine()
