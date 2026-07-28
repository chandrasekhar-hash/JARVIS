import time
from typing import Dict, Any


class SyncMetricsCollector:
    """
    Client Sync Metrics Collector tracking sync latency, bytes transferred,
    sync operations total, failed attempts, and offline replay counts.
    """

    def __init__(self):
        self.ops_total = 0
        self.bytes_uploaded = 0
        self.bytes_downloaded = 0
        self.failed_attempts = 0
        self.replayed_events_total = 0
        self.total_latency_ms = 0.0

    def record_operation(self, duration_ms: float, bytes_up: int = 0, bytes_down: int = 0, success: bool = True):
        self.ops_total += 1
        self.total_latency_ms += duration_ms
        self.bytes_uploaded += bytes_up
        self.bytes_downloaded += bytes_down
        if not success:
            self.failed_attempts += 1

    def record_replay(self, count: int):
        self.replayed_events_total += count

    def get_summary(self) -> Dict[str, Any]:
        avg_latency = (self.total_latency_ms / self.ops_total) if self.ops_total > 0 else 0.0
        return {
            "ops_total": self.ops_total,
            "failed_attempts": self.failed_attempts,
            "bytes_uploaded": self.bytes_uploaded,
            "bytes_downloaded": self.bytes_downloaded,
            "replayed_events_total": self.replayed_events_total,
            "avg_latency_ms": round(avg_latency, 3)
        }


sync_metrics = SyncMetricsCollector()
