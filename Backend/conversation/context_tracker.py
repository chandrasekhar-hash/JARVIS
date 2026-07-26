import re
import time
from typing import List, Dict, Optional, Any
from conversation.models import ConversationState, ConversationReference
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class ContextTracker:
    """
    Tracks active working context and resolves ambiguous pronouns and references
    ("that", "it", "same project", "continue", "again") using current dialogue state.
    SLA Target: Reference Resolution < 20 ms.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.event_bus = bus or event_bus
        self.reference_patterns = {
            r"\b(that|it)\b": "last_target_object",
            r"\b(same project|same one|previous one)\b": "active_topic",
            r"\b(continue|again|repeat)\b": "last_turn_text",
        }

    def resolve_references(
        self, turn_text: str, state: ConversationState
    ) -> List[ConversationReference]:
        start = time.perf_counter()
        resolved: List[ConversationReference] = []

        try:
            text_lower = turn_text.lower()

            for pattern, target_field in self.reference_patterns.items():
                match = re.search(pattern, text_lower)
                if match:
                    expr = match.group(1)
                    target_val: Optional[str] = None

                    if target_field == "last_target_object":
                        file_match = re.search(r"[\w\-\\./]+\.(py|js|ts|rs|md|json|html|css)", turn_text)
                        target_val = state.last_target_object or (file_match.group(0) if file_match else state.last_turn_text)
                    elif target_field == "active_topic":
                        target_val = state.active_topic.topic_name if state.active_topic else "active_project"
                    elif target_field == "last_turn_text":
                        target_val = state.last_turn_text

                    if target_val:
                        ref = ConversationReference(
                            expression=expr,
                            resolved_target=target_val,
                            confidence=0.90,
                            timestamp=time.time(),
                        )
                        resolved.append(ref)
                        state.resolved_references[expr] = target_val

                        self.event_bus.emit(
                            "ReferenceResolved",
                            session_id=state.session_id,
                            expression=expr,
                            resolved_target=target_val,
                        )

            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if elapsed_ms > 20.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[ContextTracker] Reference resolution SLA threshold exceeded: {elapsed_ms:.2f} ms",
                )

            log_structured(
                backend_log,
                "INFO",
                f"[ContextTracker] Resolved {len(resolved)} references for session '{state.session_id}' in {elapsed_ms:.2f} ms",
            )
            return resolved

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ContextTracker] Error resolving references: {str(e)}")
            return resolved

    def update_context(
        self, state: ConversationState, turn_text: str
    ) -> ConversationState:
        state.turn_count += 1
        state.last_turn_text = turn_text

        # Extract potential target object snippet (e.g., file paths, tool names)
        file_match = re.search(r"[\w\-\\./]+\.(py|js|ts|rs|md|json|html|css)", turn_text)
        if file_match:
            state.last_target_object = file_match.group(0)
        elif len(turn_text.split()) <= 4:
            state.last_target_object = turn_text.strip()

        state.updated_at = time.time()
        return state
