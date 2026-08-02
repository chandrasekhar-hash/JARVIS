import time
import json
from pathlib import Path
from typing import Dict, Any, List

class StartupTelemetryTracker:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.module_timings: Dict[str, float] = {}
        self.failed_modules: List[str] = []
        self.retry_count: int = 0

    def start_tracking(self):
        self.start_time = time.time()
        self.module_timings = {}
        self.failed_modules = []

    def record_module(self, module_name: str, duration_ms: float, status: str):
        self.module_timings[module_name] = round(duration_ms, 2)
        if status == "FAILED":
            self.failed_modules.append(module_name)

    def record_retry(self):
        self.retry_count += 1

    def finalize(self) -> Dict[str, Any]:
        self.end_time = time.time()
        total_duration = round((self.end_time - (self.start_time or time.time())) * 1000, 2)
        
        slowest_module = None
        slowest_time = -1.0
        for mod, duration in self.module_timings.items():
            if duration > slowest_time:
                slowest_time = duration
                slowest_module = mod

        metrics = {
            "total_startup_ms": total_duration,
            "slowest_module": slowest_module or "none",
            "slowest_module_ms": slowest_time if slowest_time >= 0 else 0,
            "failed_modules": self.failed_modules,
            "retry_count": self.retry_count,
            "module_timings": self.module_timings,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            with open(log_dir / "startup_metrics.json", "w") as f:
                json.dump(metrics, f, indent=2)
        except Exception:
            pass

        return metrics

startup_telemetry = StartupTelemetryTracker()
