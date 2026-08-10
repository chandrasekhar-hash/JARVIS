"""
Event Extractor for J.A.R.V.I.S. I2.2 V4.
Converts evidence items into structured NewsEvent instances.
"""

from typing import List
from intelligence.web.research.models import EvidenceItem, ResearchSource
from intelligence.web.temporal.models import NewsEvent, TemporalMetadata, UpdateCategory


class EventExtractor:
    """Extracts structured NewsEvent instances from evidence items."""

    def extract_events(
        self,
        evidence_items: List[EvidenceItem],
        sources: List[ResearchSource]
    ) -> List[NewsEvent]:
        """Converts evidence items into structured NewsEvent objects."""
        source_map = {s.source_id: s for s in sources}
        events: List[NewsEvent] = []

        for idx, ev in enumerate(evidence_items):
            src = source_map.get(ev.source_id)
            pub_at = src.published_at if src else None
            ret_at = src.retrieved_at if src else ""

            meta = TemporalMetadata(
                published_at=pub_at,
                event_time=pub_at,
                retrieved_at=ret_at
            )

            heading = " > ".join(ev.heading_path) if ev.heading_path else "Event"
            title = f"{heading}: {ev.text[:80]}"

            event = NewsEvent(
                event_id=f"event_{idx + 1}",
                title=title,
                description=ev.text,
                event_time=pub_at,
                first_published_at=pub_at,
                latest_update_at=pub_at,
                evidence_ids=[ev.evidence_id],
                source_ids=[ev.source_id],
                entities=[src.domain] if src else [],
                update_category=UpdateCategory.NEW_EVENT,
                temporal_metadata=meta
            )
            events.append(event)

        return events


event_extractor = EventExtractor()
