import time
import asyncio
from typing import Dict, Any, List
from axl.feature_flags import feature_flag_engine
from axl.telemetry import startup_telemetry

class SystemBootManager:
    """
    Backend Boot Orchestrator for Product 1.11 AXL.
    Manages module states (WAITING, LOADING, READY, FAILED, SKIPPED),
    required vs optional classifications, and parallel stage execution.
    """
    def __init__(self):
        self.module_states: Dict[str, str] = {
            "identity": "WAITING",
            "settings": "WAITING",
            "tool_engine": "WAITING",
            "memory": "WAITING",
            "plugins": "WAITING",
            "knowledge": "WAITING",
            "automation": "WAITING",
            "workspace": "WAITING",
            "voice": "WAITING",
            "reasoning": "WAITING"
        }
        self.required_modules = {"identity", "settings", "tool_engine"}

    def get_status(self) -> Dict[str, Any]:
        return {
            "module_states": self.module_states,
            "required_modules": list(self.required_modules)
        }

    async def initialize_all(self):
        startup_telemetry.start_tracking()

        # Phase 1: Required Identity
        await self._init_module("identity", self._init_identity_impl)

        # Phase 2: Required Settings
        await self._init_module("settings", self._init_settings_impl)

        # Phase 3: Parallel Ingestion Stage (Memory, Plugins, Workspace, Knowledge)
        await asyncio.gather(
            self._init_module("memory", self._init_memory_impl),
            self._init_module("plugins", self._init_plugins_impl),
            self._init_module("workspace", self._init_workspace_impl),
            self._init_module("knowledge", self._init_knowledge_impl),
            return_exceptions=True
        )

        # Phase 4: Dependent Engines (Tool Engine [REQUIRED], Automation, Voice, Reasoning)
        await self._init_module("tool_engine", self._init_tools_impl)

        await asyncio.gather(
            self._init_module("automation", self._init_automation_impl),
            self._init_module("voice", self._init_voice_impl),
            self._init_module("reasoning", self._init_reasoning_impl),
            return_exceptions=True
        )

        metrics = startup_telemetry.finalize()
        print(f"DEBUG_LOG: [SystemBootManager] Startup complete in {metrics['total_startup_ms']}ms. Module states: {self.module_states}")

    async def _init_module(self, name: str, func):
        # Check feature flag for optional modules if configured
        flag_map = {
            "knowledge": "ENABLE_KNOWLEDGE",
            "automation": "ENABLE_AUTOMATION",
            "workspace": "ENABLE_WORKSPACE",
            "voice": "ENABLE_VOICE",
            "reasoning": "ENABLE_REASONING"
        }
        if name in flag_map:
            flag = flag_map[name]
            if not feature_flag_engine.is_enabled(flag):
                self.module_states[name] = "SKIPPED"
                startup_telemetry.record_module(name, 0.0, "SKIPPED")
                return

        self.module_states[name] = "LOADING"
        t0 = time.time()
        try:
            res = func()
            if asyncio.iscoroutine(res):
                await res
            self.module_states[name] = "READY"
            duration = (time.time() - t0) * 1000
            startup_telemetry.record_module(name, duration, "READY")
        except Exception as e:
            self.module_states[name] = "FAILED"
            duration = (time.time() - t0) * 1000
            startup_telemetry.record_module(name, duration, "FAILED")
            print(f"DEBUG_LOG: [SystemBootManager] Module '{name}' failed initialization: {e}")
            if name in self.required_modules:
                raise RuntimeError(f"Required module '{name}' failed to initialize: {e}")

    async def _init_identity_impl(self):
        from identity.identity_manager import identity_manager
        from identity.session_manager import session_manager
        identity_manager.initialize()
        session_manager.initialize()

    async def _init_settings_impl(self):
        import config
        # Verify config loaded
        _ = config.CORS_ORIGINS

    async def _init_memory_impl(self):
        pass  # Loaded on demand or verified

    async def _init_plugins_impl(self):
        from plugins.plugin_manager import plugin_manager
        plugin_manager.discover_and_load_plugins()

    async def _init_workspace_impl(self):
        pass

    async def _init_knowledge_impl(self):
        pass

    async def _init_tools_impl(self):
        from tools.router import handle_agent_chat
        _ = handle_agent_chat

    async def _init_automation_impl(self):
        from autonomous.scheduler_engine import scheduler_engine
        scheduler_engine.start()

    async def _init_voice_impl(self):
        from tts_engines import tts_manager
        _ = tts_manager

    async def _init_reasoning_impl(self):
        from ai.router import ai_router
        _ = ai_router

system_boot_manager = SystemBootManager()
