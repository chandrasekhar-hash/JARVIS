from typing import Dict, Any, Optional, List
from tools.telemetry import log_structured, backend_log

class BaseContextProvider:
    """Abstract base class for modular Brain context providers."""
    @property
    def name(self) -> str:
        raise NotImplementedError

    def should_provide_context(self, intent: str) -> bool:
        raise NotImplementedError

    def get_context(self, intent: str) -> Optional[str]:
        raise NotImplementedError

class DesktopStateContextProvider(BaseContextProvider):
    """Provides desktop OS state context (active app, focused window, tabs, directory, clipboard)."""
    def __init__(self, manager_ref: 'DesktopContextManager'):
        self._mgr = manager_ref

    @property
    def name(self) -> str:
        return "DesktopState"

    def should_provide_context(self, intent: str) -> bool:
        intent_lower = intent.lower()
        triggers = [
            "it", "this", "that", "current", "active", "application", "app", "window", "clipboard",
            "tab", "folder", "close", "switch", "copied", "paste", "focused"
        ]
        return any(trig in intent_lower for trig in triggers)

    def get_context(self, intent: str) -> Optional[str]:
        if not self.should_provide_context(intent):
            return None

        parts = []
        if self._mgr.active_app:
            parts.append(f"Active Application: {self._mgr.active_app}")
        if self._mgr.focused_window:
            parts.append(f"Focused Window: {self._mgr.focused_window}")
        if self._mgr.active_tab:
            parts.append(f"Active Browser Tab: {self._mgr.active_tab}")
        if self._mgr.current_dir:
            parts.append(f"Current Directory: {self._mgr.current_dir}")
        if self._mgr.clipboard_cache:
            clip_snippet = self._mgr.clipboard_cache[:50] + ("..." if len(self._mgr.clipboard_cache) > 50 else "")
            parts.append(f"Clipboard Content: {repr(clip_snippet)}")

        return "\n".join(parts) if parts else None

class VisionContextProvider(BaseContextProvider):
    """Provides visual screen context (OCR text, UI layout controls, scene summary, change deltas)."""
    @property
    def name(self) -> str:
        return "Vision"

    def should_provide_context(self, intent: str) -> bool:
        intent_lower = intent.lower()
        triggers = [
            "screen", "see", "look", "view", "error", "changed", "summarize",
            "what", "which", "active", "application", "app", "window", "display",
            "dialog", "read", "describe", "button", "buttons", "text", "page"
        ]
        return any(trig in intent_lower for trig in triggers)

    def get_context(self, intent: str) -> Optional[str]:
        if not self.should_provide_context(intent):
            return None

        try:
            from vision import vision_adapter
            v_res = vision_adapter.get_brain_visual_context(intent)
            if v_res.get("has_vision"):
                return str(v_res["formatted_context"])
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[VisionContextProvider] Failed to fetch visual context: {str(e)}")

        return None

class DesktopContextManager:
    def __init__(self):
        self.active_app: Optional[str] = None
        self.focused_window: Optional[str] = None
        self.running_processes: List[str] = []
        self.clipboard_cache: Optional[str] = None
        self.active_tab: Optional[str] = None
        self.current_dir: Optional[str] = None

        # Context Provider Registry
        self._providers: List[BaseContextProvider] = [
            DesktopStateContextProvider(self),
            VisionContextProvider()
        ]

    def register_provider(self, provider: BaseContextProvider) -> None:
        """Registers a new context provider (e.g. MemoryContextProvider, PluginContextProvider)."""
        if provider not in self._providers:
            self._providers.append(provider)
            log_structured(backend_log, "INFO", f"[ContextManager] Registered provider '{provider.name}'")

    def update_from_tool_execution(self, tool_name: str, args: Dict[str, Any], result: Any = None) -> None:
        """Updates internal desktop state based on tool actions."""
        name = args.get("name") or args.get("app_name")
        if tool_name in ["app_open", "app_switch"]:
            if name:
                self.active_app = str(name)
                self.focused_window = str(name)
        elif tool_name == "app_close":
            if name and self.active_app and self.active_app.lower() == str(name).lower():
                self.active_app = None
                self.focused_window = None
        elif tool_name == "browser_open_url":
            self.active_app = "Browser"
            urls = args.get("urls", [])
            if urls:
                self.active_tab = str(urls[0])
        elif tool_name == "browser_search":
            self.active_app = "Browser"
            query = args.get("query", "")
            if query:
                self.active_tab = f"Search: {query}"
        elif tool_name == "clipboard_read" and isinstance(result, str):
            self.clipboard_cache = result
        elif tool_name == "clipboard_write":
            text = args.get("text")
            if text:
                self.clipboard_cache = str(text)
        elif tool_name == "fs_open_folder":
            folder = args.get("folder_path") or args.get("path")
            if folder:
                self.current_dir = str(folder)

        log_structured(backend_log, "INFO", f"[ContextManager] State updated: ActiveApp='{self.active_app}', ActiveTab='{self.active_tab}'")

    def should_inject_context(self, intent: str) -> bool:
        """Checks whether any registered provider has context for the intent."""
        return any(provider.should_provide_context(intent) for provider in self._providers)

    def get_context_summary(self, intent: str) -> Optional[str]:
        """Collects and merges context summaries from all active providers."""
        context_blocks: List[str] = []
        for provider in self._providers:
            try:
                block = provider.get_context(intent)
                if block:
                    context_blocks.append(block)
            except Exception as e:
                log_structured(backend_log, "WARNING", f"[ContextManager] Provider '{provider.name}' error: {str(e)}")

        return "\n\n".join(context_blocks) if context_blocks else None

desktop_context = DesktopContextManager()
