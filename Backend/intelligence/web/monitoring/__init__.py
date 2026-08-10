"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Web Monitoring & Change Detection Intelligence.
Purely additive subpackage for snapshot management, fingerprinting, content and structured diffing,
semantic change classification, explainable significance, source availability tracking, and baseline change monitoring.
"""
from intelligence.web.monitoring.models import (
    MonitorTargetType,
    SourceAvailabilityStatus,
    ObservationCompleteness,
    ChangeType,
    ChangeSignificance,
    MonitorBaselineStatus,
    SnapshotTombstone,
    MonitoringSnapshot,
    ChangeEvidence,
    ChangeFinding,
    MonitorWebRequest,
    MonitorWebResponse,
    MonitoringConfig,
)
from intelligence.web.monitoring.monitor_service import web_monitor_service, MonitorWebService

__all__ = [
    "MonitorTargetType",
    "SourceAvailabilityStatus",
    "ObservationCompleteness",
    "ChangeType",
    "ChangeSignificance",
    "MonitorBaselineStatus",
    "SnapshotTombstone",
    "MonitoringSnapshot",
    "ChangeEvidence",
    "ChangeFinding",
    "MonitorWebRequest",
    "MonitorWebResponse",
    "MonitoringConfig",
    "web_monitor_service",
    "MonitorWebService",
]
