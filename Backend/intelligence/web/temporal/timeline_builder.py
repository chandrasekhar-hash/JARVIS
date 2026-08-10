"""
Timeline Builder for J.A.R.V.I.S. I2.2 V4.
Generates ordered event sequences from verified timestamps with explicit precision.
Unknown times remain unforced; zero timestamp manufacturing.
"""

from typing import List
from intelligence.web.temporal.models import TimelineEvent, NewsEvent, TimePrecision


class TimelineBuilder:
    """Constructs ordered TimelineEvent lists."""

    def build_timeline(self, events: List[NewsEvent]) -> List[TimelineEvent]:
        """
        Orders events chronologically based on verified timestamps.
        Does not force date-only events into fake exact datetimes.
        """
        timeline: List[TimelineEvent] = []

        for idx, ev in enumerate(events):
            t_str = ev.event_time or ev.first_published_at or "Unknown Time"
            prec = ev.temporal_metadata.time_precision

            item = TimelineEvent(
                timeline_id=f"timeline_{idx + 1}",
                timestamp_str=t_str,
                precision=prec,
                summary=f"{ev.title} — {ev.description[:120]}",
                source_ids=ev.source_ids,
                evidence_ids=ev.evidence_ids
            )
            timeline.append(item)

        # Sort timeline entries with known dates first
        def sort_key(t: TimelineEvent):
            if t.timestamp_str == "Unknown Time":
                return "9999-99-99"
            return t.timestamp_str

        timeline.sort(key=sort_key)
        return timeline


timeline_builder = TimelineBuilder()
