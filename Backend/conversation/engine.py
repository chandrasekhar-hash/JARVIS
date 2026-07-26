import time
import asyncio
from typing import Dict, List, Optional, Any
from conversation.models import (
    ConversationSession,
    ConversationState,
    ConversationSummary,
    ContinuityMetrics,
    ConversationResult,
)
from conversation.interfaces import (
    ISessionManager,
    ITopicManager,
    IContextTracker,
    IContinuityValidator,
)
from conversation.session_manager import SessionManager
from conversation.topic_manager import TopicManager
from conversation.context_tracker import ContextTracker
from conversation.continuity_validator import ContinuityValidator
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class ConversationContinuityEngine:
    """
    Main Conversation Continuity Engine for Milestone 7.5.
    Maintains multi-turn conversation coherence, tracks topic shifts, resolves references,
    generates hierarchical summaries, and validates continuity.
    SLA Target: Full Pipeline < 100 ms total latency.
    Does NOT execute workflows, predict goals, modify preferences, or optimize strategies.
    """

    def __init__(
        self,
        session_manager: Optional[ISessionManager] = None,
        topic_manager: Optional[ITopicManager] = None,
        context_tracker: Optional[IContextTracker] = None,
        validator: Optional[IContinuityValidator] = None,
        bus: Optional[EventBus] = None,
    ):
        self.event_bus = bus or event_bus
        self.session_manager = session_manager or SessionManager(bus=self.event_bus)
        self.topic_manager = topic_manager or TopicManager(bus=self.event_bus)
        self.context_tracker = context_tracker or ContextTracker(bus=self.event_bus)
        self.validator = validator or ContinuityValidator(bus=self.event_bus)
        self._states: Dict[str, ConversationState] = {}

    def get_state(self, session_id: str) -> ConversationState:
        if session_id not in self._states:
            self._states[session_id] = ConversationState(session_id=session_id)
        return self._states[session_id]

    async def process_turn(
        self,
        session_id: str,
        turn_text: str,
        cognitive_context: Any = None,
        prediction_result: Any = None,
    ) -> ConversationResult:
        pipeline_start = time.perf_counter()
        try:
            # Step 1 & 2: Load/Restore Session (< 30 ms SLA)
            restore_start = time.perf_counter()
            session = self.session_manager.restore_session(session_id)
            if not session:
                # Fallback create session if missing/expired
                session = self.session_manager.create_session(user_id="default_user")
                session_id = session.session_id

            session_restore_ms = (time.perf_counter() - restore_start) * 1000.0

            # Step 3: Restore Conversation State
            state = self.get_state(session_id)

            # Step 4: Resolve References ("that", "it", "same", "continue") (< 20 ms SLA)
            ref_start = time.perf_counter()
            resolved_refs = self.context_tracker.resolve_references(turn_text, state)
            reference_resolution_ms = (time.perf_counter() - ref_start) * 1000.0

            # Step 5: Track Topic (< 20 ms SLA)
            topic_start = time.perf_counter()
            self.topic_manager.track_topic(turn_text, state)
            topic_tracking_ms = (time.perf_counter() - topic_start) * 1000.0

            # Step 6: Update Context
            self.context_tracker.update_context(state, turn_text)

            # Step 7: Generate Conversation Summaries (short, working, long-term)
            active_topic_name = state.active_topic.topic_name if state.active_topic else "general"
            short_summary = f"Turn {state.turn_count}: {turn_text[:60]}"
            working_summary = f"Session '{session_id}' at turn {state.turn_count} under topic '{active_topic_name}'."
            long_term_summary = f"Dialogue history under '{active_topic_name}' with {state.turn_count} interaction turns."

            summary = ConversationSummary(
                short_summary=short_summary,
                working_summary=working_summary,
                long_term_summary=long_term_summary,
                timestamp=time.time(),
            )

            # Step 8: Validate Continuity
            validation = self.validator.validate_continuity(state, summary)

            pipeline_ms = (time.perf_counter() - pipeline_start) * 1000.0

            metrics = ContinuityMetrics(
                session_restore_time_ms=session_restore_ms,
                reference_resolution_time_ms=reference_resolution_ms,
                topic_tracking_time_ms=topic_tracking_ms,
                pipeline_time_ms=pipeline_ms,
                timestamp=time.time(),
            )

            # Step 9: Publish Events
            self.event_bus.emit(
                "ConversationUpdated",
                session_id=session_id,
                turn_count=state.turn_count,
                active_topic=active_topic_name,
            )

            self.event_bus.emit(
                "ConversationSummarised",
                session_id=session_id,
                short_summary=short_summary,
            )

            if pipeline_ms > 100.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[ConversationContinuityEngine] Full Pipeline SLA threshold exceeded: {pipeline_ms:.2f} ms",
                )

            log_structured(
                backend_log,
                "INFO",
                f"[ConversationContinuityEngine] Processed turn {state.turn_count} for session '{session_id}' in {pipeline_ms:.2f} ms",
            )

            # Step 10: Return ConversationResult
            return ConversationResult(
                success=True,
                session=session,
                state=state,
                resolved_references=resolved_refs,
                summary=summary,
                validation=validation,
                metrics=metrics,
            )

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ConversationContinuityEngine] Pipeline error: {str(e)}")
            pipeline_ms = (time.perf_counter() - pipeline_start) * 1000.0
            return ConversationResult(
                success=False,
                error_message=f"Continuity engine exception: {str(e)}",
                metrics=ContinuityMetrics(pipeline_time_ms=pipeline_ms),
            )


# Default global instance
conversation_continuity_engine = ConversationContinuityEngine()
