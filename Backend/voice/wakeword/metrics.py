import time
from typing import Dict, Any, Optional


class WakeWordMetrics:
    """
    Performance and diagnostic metrics collector for Wake Word Engine.
    """

    def __init__(self):
        self.frames_processed: int = 0
        self.detections_count: int = 0
        self.rejected_count: int = 0
        self.false_positives: int = 0
        self.last_detection_timestamp: Optional[float] = None
        self.last_detection_keyword: Optional[str] = None
        self.last_detection_confidence: Optional[float] = None
        self.error_count: int = 0
        self.cpu_usage_percent: float = 0.5
        self.memory_mb: float = 24.5
        self.start_timestamp: float = time.time()

    def record_frame(self):
        self.frames_processed += 1

    def record_detection(self, keyword: str, confidence: float):
        self.detections_count += 1
        self.last_detection_timestamp = time.time()
        self.last_detection_keyword = keyword
        self.last_detection_confidence = confidence

    def record_rejection(self):
        self.rejected_count += 1

    def record_error(self):
        self.error_count += 1

    def get_summary(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_timestamp
        return {
            "uptime_seconds": round(uptime, 2),
            "frames_processed": self.frames_processed,
            "detections_count": self.detections_count,
            "rejected_count": self.rejected_count,
            "false_positives": self.false_positives,
            "error_count": self.error_count,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_mb": self.memory_mb,
            "last_detection_timestamp": self.last_detection_timestamp,
            "last_detection_keyword": self.last_detection_keyword,
            "last_detection_confidence": self.last_detection_confidence
        }


wake_word_metrics = WakeWordMetrics()
