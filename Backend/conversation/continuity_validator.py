import time
from typing import List, Optional
from conversation.models import ConversationState, ConversationSummary, ContinuityValidation
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class ContinuityValidator:
    """
    Validates context consistency, topic consistency, reference validity, session integrity,
    and conversation coherence across multi-turn interactions.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.event_bus = bus or event_bus

    def validate_continuity(
        self, state: ConversationState, summary: Optional[ConversationSummary] = None
    ) -> ContinuityValidation:
        issues: List[str] = []
        topic_score = 1.0
        reference_score = 1.0
        coherence_score = 1.0
        session_integrity = True

        try:
            if not state or not state.session_id:
                session_integrity = False
                issues.append("Missing or invalid conversation session ID.")

            # Topic consistency validation
            if len(state.topic_history) > 5:
                # Frequent topic changes might indicate low topic consistency
                recent_shifts = len([t for t in state.topic_history[-5:] if t.reason == "keyword_shift"])
                if recent_shifts > 3:
                    topic_score = 0.60
                    issues.append("High topic transition frequency detected.")

            # Reference validity validation
            if state.resolved_references:
                invalid_refs = [
                    expr for expr, target in state.resolved_references.items() if not target
                ]
                if invalid_refs:
                    reference_score = 0.50
                    issues.append(f"Unresolved references present: {invalid_refs}")

            # Coherence calculation
            coherence_score = round((topic_score + reference_score + (1.0 if session_integrity else 0.0)) / 3.0, 2)
            is_consistent = coherence_score >= 0.70 and session_integrity

            validation = ContinuityValidation(
                is_consistent=is_consistent,
                topic_consistency_score=topic_score,
                reference_validity_score=reference_score,
                session_integrity=session_integrity,
                coherence_score=coherence_score,
                issues=issues,
            )

            self.event_bus.emit(
                "ContinuityValidated",
                session_id=state.session_id if state else "unknown",
                is_consistent=is_consistent,
                coherence_score=coherence_score,
            )

            log_structured(
                backend_log,
                "INFO",
                f"[ContinuityValidator] Validated session '{state.session_id if state else 'unknown'}': Coherence={coherence_score:.2f}, Consistent={is_consistent}",
            )
            return validation

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ContinuityValidator] Validation error: {str(e)}")
            return ContinuityValidation(
                is_consistent=False,
                coherence_score=0.0,
                session_integrity=False,
                issues=[f"Validation exception: {str(e)}"],
            )
