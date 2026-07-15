# Backward compatibility mapping tools.logger -> tools.telemetry
from tools.telemetry import (
    log_structured,
    backend_log,
    tools_log,
    perf_log,
    telemetry_manager
)

class BackwardPerfTracker:
    def start(self, key: str):
        pass
    def stop(self, key: str) -> float:
        return 0.0

perf_tracker = BackwardPerfTracker()

def log_tool_exec(tool_name: str, args: dict, safety_level: str):
    log_structured(
        tools_log, 
        "INFO", 
        f"Executing tool '{tool_name}'", 
        tool_name=tool_name, 
        args=args, 
        safety_level=safety_level
    )

def log_tool_success(tool_name: str, elapsed: float):
    # Record metrics
    telemetry_manager.record_latency("tool_latency", elapsed)
    if tool_name.startswith("browser_"):
        telemetry_manager.record_latency("browser_latency", elapsed)
        telemetry_manager.increment_counter("browser_operations")
    elif tool_name.startswith("fs_"):
        telemetry_manager.record_latency("file_latency", elapsed)
        telemetry_manager.increment_counter("file_operations")
        
    log_structured(
        tools_log, 
        "INFO", 
        f"Tool execution succeeded for '{tool_name}'", 
        tool_name=tool_name, 
        execution_time=elapsed, 
        status="success"
    )

def log_tool_failure(tool_name: str, error: str):
    log_structured(
        tools_log, 
        "ERROR", 
        f"Tool execution failed for '{tool_name}'", 
        tool_name=tool_name, 
        error=error, 
        status="failure"
    )

def log_tool_timeout(tool_name: str, timeout: float):
    log_structured(
        tools_log, 
        "ERROR", 
        f"Tool execution timed out for '{tool_name}' after {timeout}s", 
        tool_name=tool_name, 
        error="timeout", 
        status="timeout"
    )

def log_safety_confirmation(action: str, confirmed: bool):
    status = "Approved" if confirmed else "Requested/Pending"
    log_structured(
        backend_log, 
        "INFO", 
        f"Safety confirmation for '{action}': {status}", 
        action=action, 
        confirmed=confirmed
    )

def log_user_interruption():
    log_structured(backend_log, "WARNING", "User interruption: active SSE connection aborted by user.")

def log_backend_cancellation(task_name: str):
    log_structured(backend_log, "WARNING", f"Backend cancellation: Task '{task_name}' cancelled.")
