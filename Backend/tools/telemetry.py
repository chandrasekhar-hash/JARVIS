import os
import sys
import time
import json
import logging
import asyncio
import contextvars
import psutil
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, List

# Create logs directory
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Context variables for tracing requests across async frames
request_id_var = contextvars.ContextVar("request_id", default="")
session_id_var = contextvars.ContextVar("session_id", default="")
conversation_id_var = contextvars.ContextVar("conversation_id", default="")

# Basic logging format configuration
log_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
root_logger = logging.getLogger("JARVIS_ROOT")

def setup_rotating_logger(name: str, filename: str) -> logging.Logger:
    """Sets up a rotating file logger for JSON output."""
    l = logging.getLogger(name)
    l.setLevel(logging.INFO)
    l.propagate = False
    
    # Remove existing handlers to avoid duplicates on re-import
    l.handlers = []
    
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    l.addHandler(handler)
    return l

# Create rotating file loggers
backend_log = setup_rotating_logger("jarvis_backend", "backend.log")
tools_log = setup_rotating_logger("jarvis_tools", "tools.log")
errors_log = setup_rotating_logger("jarvis_errors", "errors.log")
perf_log = setup_rotating_logger("jarvis_perf", "performance.log")

def log_structured(logger_obj: logging.Logger, level: str, message: str, **kwargs):
    """Formats and writes a structured JSON log entry to file and console."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "request_id": request_id_var.get(),
        "session_id": session_id_var.get(),
        "conversation_id": conversation_id_var.get(),
        "level": level,
        "message": message,
        **kwargs
    }
    serialized = json.dumps(entry)
    # Write to target rotating log file
    logger_obj.info(serialized)
    
    # Write warnings and errors to errors.log automatically
    if level in ["WARNING", "ERROR", "CRITICAL"] and logger_obj != errors_log:
        errors_log.error(serialized)
        
    # Standard terminal console output for developer visibility
    console_msg = f"[{level}] {message}"
    if "tool_name" in kwargs:
        console_msg += f" | Tool: {kwargs['tool_name']}"
    if "execution_time" in kwargs:
        console_msg += f" | Elapsed: {kwargs['execution_time']:.4f}s"
    if "status" in kwargs:
        console_msg += f" | Status: {kwargs['status']}"
    if "error" in kwargs and kwargs["error"]:
        console_msg += f" | Error: {kwargs['error']}"
        
    if level == "INFO":
        root_logger.info(console_msg)
    elif level == "WARNING":
        root_logger.warning(console_msg)
    elif level in ["ERROR", "CRITICAL"]:
        root_logger.error(console_msg)

class RollingMetric:
    def __init__(self):
        # Stores (timestamp, value)
        self.history: List[tuple] = []
        self.session_history: List[tuple] = []
        
    def record(self, value: float):
        t = time.time()
        self.history.append((t, value))
        self.session_history.append((t, value))
        self.cleanup_old()
        
    def cleanup_old(self):
        # Keep only last 5 minutes (300 seconds) in sliding history
        now = time.time()
        self.history = [(t, v) for t, v in self.history if now - t <= 300]
        
    def get_stats(self, duration_sec: float = None) -> dict:
        now = time.time()
        if duration_sec:
            values = [v for t, v in self.history if now - t <= duration_sec]
        else:
            values = [v for t, v in self.session_history]
            
        if not values:
            return {"avg": 0.0, "p95": 0.0, "max": 0.0, "count": 0}
            
        sorted_vals = sorted(values)
        count = len(sorted_vals)
        avg_val = sum(sorted_vals) / count
        max_val = sorted_vals[-1]
        p95_idx = int(count * 0.95)
        p95_val = sorted_vals[min(p95_idx, count - 1)]
        
        return {
            "avg": round(avg_val, 4),
            "p95": round(p95_val, 4),
            "max": round(max_val, 4),
            "count": count
        }

class ObservabilityManager:
    def __init__(self):
        self.metrics = {
            "llm_latency": RollingMetric(),
            "tool_latency": RollingMetric(),
            "tts_latency": RollingMetric(),
            "browser_latency": RollingMetric(),
            "file_latency": RollingMetric(),
            "total_latency": RollingMetric()
        }
        self.counters = {
            "llm_requests": 0,
            "tts_requests": 0,
            "browser_operations": 0,
            "file_operations": 0,
            "active_conversations": 0,
            "active_tool_executions": 0
        }
        
    def record_latency(self, metric_name: str, value: float):
        if metric_name in self.metrics:
            self.metrics[metric_name].record(value)
            
    def increment_counter(self, counter_name: str):
        if counter_name in self.counters:
            self.counters[counter_name] += 1
            
    def decrement_counter(self, counter_name: str):
        if counter_name in self.counters:
            self.counters[counter_name] = max(0, self.counters[counter_name] - 1)

    def get_summary(self) -> dict:
        summary = {}
        # Get statistics for different intervals
        intervals = {
            "1m": 60,
            "5m": 300,
            "session": None
        }
        for metric, rolling in self.metrics.items():
            summary[metric] = {}
            for label, duration in intervals.items():
                summary[metric][label] = rolling.get_stats(duration)
                
        summary["counts"] = self.counters
        summary["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "ram_mb": psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        }
        return summary

# Global telemetry manager instance
telemetry_manager = ObservabilityManager()

class TaskWatchdog:
    def __init__(self):
        # Maps task_id -> {"task": Task, "start_time": float, "timeout": float, "description": str}
        self.tasks: Dict[str, dict] = {}
        self.watchdog_task: asyncio.Task = None

    def register_task(self, task: asyncio.Task, name: str, timeout: float = None):
        """Registers a background asyncio task under the watchdog manager."""
        task_id = str(id(task))
        self.tasks[task_id] = {
            "task": task,
            "start_time": time.time(),
            "timeout": timeout,
            "description": name
        }
        # Discard once completed
        task.add_done_callback(lambda t: self.tasks.pop(task_id, None))

    def start_watchdog(self):
        if not self.watchdog_task or self.watchdog_task.done():
            self.watchdog_task = asyncio.create_task(self._watch_loop())

    async def _watch_loop(self):
        print("DEBUG_LOG: [Telemetry] Task Watchdog active.")
        while True:
            now = time.time()
            for task_id, info in list(self.tasks.items()):
                task = info["task"]
                if task.done():
                    self.tasks.pop(task_id, None)
                    continue
                    
                timeout = info["timeout"]
                if timeout:
                    elapsed = now - info["start_time"]
                    if elapsed > timeout:
                        msg = f"Task Watchdog triggered: Task '{info['description']}' exceeded timeout limit of {timeout}s (elapsed: {elapsed:.2f}s). Cancelling."
                        log_structured(errors_log, "ERROR", msg, task_id=task_id, error="timeout_exceeded")
                        task.cancel()
                        self.tasks.pop(task_id, None)
                        
            await asyncio.sleep(1.0)

    def cancel_all_tasks(self):
        """Cancels all active background tasks cleanly on shutdown/cancellations."""
        for task_id, info in list(self.tasks.items()):
            task = info["task"]
            if not task.done():
                msg = f"Crash/Shutdown Recovery: Cancelling orphaned task '{info['description']}'"
                log_structured(backend_log, "WARNING", msg)
                task.cancel()
        self.tasks.clear()

task_watchdog = TaskWatchdog()
