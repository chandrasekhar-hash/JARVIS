import re
import time
from typing import Optional, Dict, List
from conversation.models import Topic, TopicTransition, ConversationState
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class TopicManager:
    """
    Tracks active conversation topic, subtopics, and transitions.
    SLA Target: Topic Tracking < 20 ms.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.event_bus = bus or event_bus
        self.topic_keywords = {
            "software_engineering": ["code", "python", "test", "build", "git", "bug", "refactor"],
            "system_administration": ["system", "terminal", "process", "service", "logs", "disk"],
            "web_browsing": ["browser", "search", "url", "site", "page", "google"],
            "general_inquiry": ["help", "explain", "what", "how", "tell"],
        }

    def track_topic(self, turn_text: str, state: ConversationState) -> Optional[TopicTransition]:
        start = time.perf_counter()
        try:
            text_lower = turn_text.lower()
            detected_topic_name = "general_inquiry"

            for topic_name, keywords in self.topic_keywords.items():
                if any(re.search(r"\b" + re.escape(kw) + r"\b", text_lower) for kw in keywords):
                    detected_topic_name = topic_name
                    break

            current_topic_name = state.active_topic.topic_name if state.active_topic else None
            transition: Optional[TopicTransition] = None

            if current_topic_name != detected_topic_name:
                transition = TopicTransition(
                    from_topic=current_topic_name,
                    to_topic=detected_topic_name,
                    reason="keyword_shift",
                    timestamp=time.time(),
                )
                state.active_topic = Topic(
                    topic_name=detected_topic_name,
                    confidence=0.85,
                    started_at=time.time(),
                )
                state.topic_history.append(transition)

                self.event_bus.emit(
                    "TopicChanged",
                    session_id=state.session_id,
                    from_topic=current_topic_name,
                    to_topic=detected_topic_name,
                    reason="keyword_shift",
                )

            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if elapsed_ms > 20.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[TopicManager] Topic tracking SLA threshold exceeded: {elapsed_ms:.2f} ms",
                )

            log_structured(
                backend_log,
                "INFO",
                f"[TopicManager] Topic for session '{state.session_id}': '{detected_topic_name}' in {elapsed_ms:.2f} ms",
            )
            return transition

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[TopicManager] Error tracking topic: {str(e)}")
            return None
