import sys
import inspect
import asyncio
from typing import Callable, Dict, Any, List
from brain.permissions import permission_manager
from tools.locks import get_tool_lock, destructive_lock
from tools.logger import perf_tracker, log_tool_exec, log_tool_success, log_tool_failure, log_tool_timeout

class RegisteredTool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        safety_level: str,  # "safe", "confirmation_required", "restricted"
        supported_platforms: List[str],  # e.g., ["windows", "macos", "linux"]
        func: Callable
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.safety_level = safety_level
        self.supported_platforms = [p.lower() for p in supported_platforms]
        self.func = func

    def to_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        safety_level: str = "safe",
        supported_platforms: List[str] = None
    ):
        if supported_platforms is None:
            supported_platforms = ["windows", "macos", "linux"]
        
        def decorator(func: Callable):
            tool = RegisteredTool(
                name=name,
                description=description,
                parameters=parameters,
                safety_level=safety_level,
                supported_platforms=supported_platforms,
                func=func
            )
            self.tools[name] = tool
            # Automatically register safety level with the Permission Manager
            permission_manager.register_tool_permission(name, safety_level)
            return func
        return decorator

    def get_current_platform(self) -> str:
        current_platform = sys.platform
        if current_platform == "win32":
            return "windows"
        elif current_platform == "darwin":
            return "macos"
        elif current_platform.startswith("linux"):
            return "linux"
        return "unknown"

    def is_supported_on_current_platform(self, name: str) -> bool:
        if name not in self.tools:
            return False
        
        plat = self.get_current_platform()
        supported = self.tools[name].supported_platforms
        return plat in supported or "all" in supported

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = []
        for name, tool in self.tools.items():
            if self.is_supported_on_current_platform(name):
                schemas.append(tool.to_schema())
        return schemas

    async def execute(self, tool_name: str, **kwargs) -> Any:
        """
        Executes a tool asynchronously.
        Handles platform support, prerequisite validation, safety permissions,
        concurrency locks, argument validation/coercion, structured logging,
        and execution timeouts.

        NOTE: The first positional parameter is named `tool_name` (not `name`) to
        prevent collision with tools whose own arguments are also called `name`
        (e.g. app_open(name), app_switch(name), app_close(name)).
        """
        print(f"DEBUG_LOG: [Registry.execute] tool_name={tool_name!r} | kwargs={kwargs}")
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found.")
        
        if not self.is_supported_on_current_platform(tool_name):
            raise RuntimeError(
                f"Tool '{tool_name}' is not supported on the current platform ({self.get_current_platform()})."
            )
            
        tool = self.tools[tool_name]
        
        # 1. Prerequisite verification
        if hasattr(tool.func, "check_prerequisites"):
            prereq_err = tool.func.check_prerequisites(**kwargs)
            if prereq_err:
                raise RuntimeError(f"Prerequisites validation failed: {prereq_err}")
                
        # 2. Permission manager check
        perm_status = permission_manager.verify_permission(tool_name, kwargs)
        if perm_status == "requires_confirmation":
            return f"[REQUIRES_CONFIRMATION] Action '{tool_name}' requires user confirmation."
        elif perm_status == "requires_restricted_approval":
            return f"[REQUIRES_RESTRICTED_APPROVAL] Restricted action '{tool_name}' requires explicit approval."
        elif perm_status == "denied":
            return f"[PERMISSION_DENIED] Action '{tool_name}' is blocked by security manager."

        # 3. Lock execution & execute tool
        tool_lock = await get_tool_lock(tool_name)
        is_destructive = tool.safety_level in ["confirmation_required", "restricted"]
        
        async with tool_lock:
            if is_destructive:
                # Enforce that no two destructive operations run simultaneously
                async with destructive_lock:
                    return await self._run_with_timeout(tool, kwargs)
            else:
                return await self._run_with_timeout(tool, kwargs)

    async def _run_with_timeout(self, tool: RegisteredTool, kwargs: dict) -> Any:
        name = tool.name
        
        # Validate signature and type-coerce inputs
        sig = inspect.signature(tool.func)
        valid_args = {}
        for param_name, param in sig.parameters.items():
            if param_name in kwargs:
                val = kwargs[param_name]
                # Coerce boolean strings to proper python booleans
                if param.annotation == bool and not isinstance(val, bool):
                    if str(val).lower() in ["true", "1", "yes"]:
                        val = True
                    elif str(val).lower() in ["false", "0", "no"]:
                        val = False
                valid_args[param_name] = val
            elif param.default is inspect.Parameter.empty:
                raise ValueError(f"Missing required parameter '{param_name}' for tool '{name}'")
                
        log_tool_exec(name, valid_args, tool.safety_level)
        perf_tracker.start(name)
        
        loop = asyncio.get_running_loop()
        try:
            if asyncio.iscoroutinefunction(tool.func):
                result = await asyncio.wait_for(tool.func(**valid_args), timeout=10.0)
            else:
                # Wrap blocking sync calls in run_in_executor to avoid blocking the main loop
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: tool.func(**valid_args)),
                    timeout=10.0
                )
            elapsed = perf_tracker.stop(name)
            log_tool_success(name, elapsed)
            return result
        except asyncio.TimeoutError:
            perf_tracker.stop(name)
            log_tool_timeout(name, 10.0)
            raise TimeoutError(f"Tool '{name}' execution timed out after 10.0s.")
        except Exception as e:
            perf_tracker.stop(name)
            log_tool_failure(name, str(e))
            raise

registry = ToolRegistry()

# ── Startup self-check ────────────────────────────────────────────────────────
# Asserts the execute() signature is correct at import time.
# If someone accidentally renames tool_name back to name, this fails immediately.
import inspect as _inspect
_exec_params = list(_inspect.signature(ToolRegistry.execute).parameters.keys())
assert "tool_name" in _exec_params, (
    f"FATAL: ToolRegistry.execute() must use 'tool_name' as its first parameter "
    f"to avoid collision with tool arguments also named 'name'. "
    f"Current params: {_exec_params}"
)
assert "name" not in _exec_params, (
    f"FATAL: ToolRegistry.execute() has 'name' as a parameter — this will collide "
    f"with app_open/app_close/app_switch which all accept a 'name' argument. "
    f"Rename to 'tool_name'. Current params: {_exec_params}"
)
print(f"DEBUG_LOG: [Registry] Startup self-check passed. execute() params: {_exec_params}")
