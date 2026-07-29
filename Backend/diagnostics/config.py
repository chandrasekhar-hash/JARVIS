"""
Configuration Layer for J.A.R.V.I.S. Phase V1.8 Diagnostics & Observability Platform.
Centralized settings for logging, tracing, event timeline buffer limits, export directories, and health checks.
"""
from dataclasses import dataclass, field


@dataclass
class DiagnosticsConfig:
    """Centralized Developer Diagnostics Configuration."""
    log_level: str = "INFO"
    enable_json_logging: bool = True
    enable_console_logging: bool = True
    enable_file_logging: bool = True
    log_file_path: str = "logs/jarvis_diagnostics.log"
    trace_sample_rate: float = 1.0
    max_timeline_records: int = 2000
    export_directory: str = "logs/exports"
    health_check_interval_sec: float = 5.0
    runtime_check_interval_sec: float = 5.0
    enable_auto_export: bool = False


# Global default configuration instance
diagnostics_config = DiagnosticsConfig()
