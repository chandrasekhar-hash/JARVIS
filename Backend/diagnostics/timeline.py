"""
Event Timeline Recorder for J.A.R.V.I.S. Phase V1.8.
Captures chronological event timeline records and supports timeline event replay.
"""
import time
import logging
from typing import List, Dict, Optional, Any
from .interfaces import ITimelineRecorder
from .models import TimelineRecord, EventRecord

logger = logging.getLogger("JARVIS_TimelineRecorder")


class TimelineRecorder(ITimelineRecorder):
    """
    Chronological Event Timeline Recorder with event replay capabilities.
    """

    def __init__(self, capacity: int = 2000):
        self.capacity = capacity
        self._records: List[TimelineRecord] = []

    def record_event(
        self,
        event_name: str,
        subsystem: str,
        session_id: str = "",
        correlation_id: str = "",
        **payload,
    ) -> TimelineRecord:
        record = TimelineRecord(
            event_name=event_name,
            subsystem=subsystem,
            session_id=session_id,
            correlation_id=correlation_id,
            timestamp=time.time(),
            payload=payload,
        )

        self._records.append(record)
        if len(self._records) > self.capacity:
            self._records.pop(0)

        logger.debug(f"[TimelineRecorder] Event '{event_name}' recorded for subsystem '{subsystem}'.")
        return record

    def get_timeline(self, session_id: Optional[str] = None) -> List[TimelineRecord]:
        if session_id:
            return [r for r in self._records if r.session_id == session_id]
        return list(self._records)

    def replay_timeline(self, session_id: Optional[str] = None) -> List[EventRecord]:
        records = self.get_timeline(session_id=session_id)
        return [
            EventRecord(
                event_type=r.event_name,
                timestamp=r.timestamp,
                source=r.subsystem,
                details=r.payload,
            )
            for r in records
        ]

    def clear(self) -> None:
        self._records.clear()
