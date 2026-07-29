"""
Master Conversation Continuity Engine for J.A.R.V.I.S. Phase V1.3.
Maintains multi-turn conversation coherence, state machine transitions, intent processing,
response provider abstractions, context trimming, and SpeechFinalEvent integration.
SLA Target: Full Pipeline < 100 ms total latency.
"""
import time
import inspect
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Union

from conversation.models import (
    ConversationSession,
    ConversationState,
    ConversationSummary,
    ContinuityMetrics,
    ContinuityValidation,
    ConversationResult,
    ConversationTurn,
    TurnState,
    IntentResult,
)
from conversation.interfaces import (
    ISessionManager,
    ITopicManager,
    IContextTracker,
    IContinuityValidator,
    IConversationContinuityEngine,
)
from conversation.session_manager import SessionManager
from conversation.topic_manager import TopicManager
from conversation.context_tracker import ContextTracker
from conversation.continuity_validator import ContinuityValidator
from conversation.state_machine import ConversationStateMachine, ConversationStateEnum
from conversation.intent_processor import IntentProcessor
from conversation.response_provider import IResponseProvider, ResponseProviderFactory
from conversation.metrics import conversation_metrics, ConversationMetrics
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log

logger = logging.getLogger("JARVIS_ConversationEngine")


class ConversationContinuityEngine(IConversationContinuityEngine):
    """
    Production-grade Conversation Engine orchestrating turn processing, reference resolution,
    topic tracking, intent classification, response provider generation, history trimming,
    and EventBus dispatches for SpeechFinalEvent integration.
    """

    def __init__(
        self,
        session_manager: Optional[ISessionManager] = None,
        topic_manager: Optional[ITopicManager] = None,
        context_tracker: Optional[IContextTracker] = None,
        validator: Optional[IContinuityValidator] = None,
        intent_processor: Optional[IntentProcessor] = None,
        response_provider: Optional[IResponseProvider] = None,
        bus: Optional[EventBus] = None,
        max_history_turns: int = 20,
    ):
        self.event_bus = bus or event_bus
        self.session_manager = session_manager or SessionManager(bus=self.event_bus)
        self.topic_manager = topic_manager or TopicManager(bus=self.event_bus)
        self.context_tracker = context_tracker or ContextTracker(bus=self.event_bus)
        self.validator = validator or ContinuityValidator(bus=self.event_bus)
        self.intent_processor = intent_processor or IntentProcessor()
        self.response_provider = response_provider or ResponseProviderFactory.create_provider("local")
        self.metrics = conversation_metrics
        self.max_history_turns = max_history_turns

        self._states: Dict[str, ConversationState] = {}
        self._state_machines: Dict[str, ConversationStateMachine] = {}
        self._last_processed_transcripts: Dict[str, str] = {}

        # Subscribe to V1.2 Speech Engine events
        self._subscribe_speech_events()

    def _subscribe_speech_events(self) -> None:
        """Subscribes to V1.2 SpeechFinalEvent over EventBus."""
        try:
            self.event_bus.subscribe("speech_final", self._handle_speech_final_event)
        except Exception as e:
            logger.warning(f"[ConversationEngine] Could not subscribe to speech_final event: {e}")

    def _handle_speech_final_event(self, event: Any = None, **kwargs) -> None:
        """Handles incoming SpeechFinalEvent from V1.2 Speech Engine."""
        data = event.data if hasattr(event, "data") else (event if isinstance(event, dict) else kwargs)
        transcript = (data.get("transcript") if isinstance(data, dict) else "").strip()
        speech_session_id = data.get("session_id", "") if isinstance(data, dict) else ""

        if not transcript:
            return

        # Deduplicate identical consecutive speech final events
        last_text = self._last_processed_transcripts.get(speech_session_id)
        if last_text == transcript:
            logger.info(f"[ConversationEngine] Ignored duplicate SpeechFinalEvent transcript for session '{speech_session_id}'.")
            return

        self._last_processed_transcripts[speech_session_id] = transcript

        # Trigger turn processing asynchronously
        if inspect.iscoroutinefunction(self.process_turn):
            asyncio.create_task(self.process_turn(session_id=speech_session_id, turn_text=transcript))
        else:
            asyncio.run(self.process_turn(session_id=speech_session_id, turn_text=transcript))

    def set_response_provider(self, provider: IResponseProvider) -> None:
        """Updates the active response provider dynamically."""
        self.response_provider = provider

    def get_state(self, session_id: str) -> ConversationState:
        """Retrieves or creates conversation state for session."""
        if session_id not in self._states:
            self._states[session_id] = ConversationState(session_id=session_id)
        return self._states[session_id]

    def get_state_machine(self, session_id: str) -> ConversationStateMachine:
        """Retrieves or creates state machine for session."""
        if session_id not in self._state_machines:
            self._state_machines[session_id] = ConversationStateMachine()
        return self._state_machines[session_id]

    def start_session(self, user_id: str = "default_user") -> ConversationSession:
        """Starts a new conversation session."""
        session = self.session_manager.create_session(user_id=user_id)
        self.get_state(session.session_id)
        self.get_state_machine(session.session_id)
        self.metrics.total_sessions += 1
        return session

    def end_session(self, session_id: str) -> bool:
        """Ends an active conversation session."""
        success = self.session_manager.end_session(session_id)
        if session_id in self._states:
            del self._states[session_id]
        if session_id in self._state_machines:
            del self._state_machines[session_id]
        return success

    def cancel_turn(self, session_id: str) -> bool:
        """Cancels active turn execution for specified session."""
        sm = self.get_state_machine(session_id)
        sm.transition_to(ConversationStateEnum.CANCELLED)
        self.metrics.total_cancellations += 1

        state = self.get_state(session_id)
        if state.history:
            state.history[-1].state = TurnState.CANCELLED

        self.event_bus.emit(
            "ConversationCancelled",
            session_id=session_id,
            reason="turn_cancellation",
        )
        sm.transition_to(ConversationStateEnum.IDLE)
        return True

    def get_history(self, session_id: str) -> List[ConversationTurn]:
        """Returns turn history for specified session."""
        state = self.get_state(session_id)
        return list(state.history)

    def clear_history(self, session_id: str) -> bool:
        """Clears turn history for specified session."""
        state = self.get_state(session_id)
        state.history.clear()
        state.turn_count = 0
        return True

    def reset_session(self, session_id: str) -> bool:
        """Resets session state, topic history, and references."""
        self.clear_history(session_id)
        state = self.get_state(session_id)
        state.active_topic = None
        state.topic_history.clear()
        state.resolved_references.clear()
        sm = self.get_state_machine(session_id)
        sm.reset()
        return True

    async def process_turn(
        self,
        session_id: str,
        turn_text: str,
        cognitive_context: Any = None,
        prediction_result: Any = None,
    ) -> ConversationResult:
        """
        Executes atomic turn processing pipeline:
        Input Validation -> Restore Session -> Resolve References -> Track Topic -> Intent -> Response Provider -> Summaries -> Lifecycle Events
        """
        pipeline_start = time.perf_counter()
        turn_text_clean = turn_text.strip() if turn_text else ""

        # 1. Validation & Empty Input Protection
        if not turn_text_clean:
            return ConversationResult(
                success=False,
                error_message="Empty or whitespace turn text provided.",
            )

        sm = self.get_state_machine(session_id)
        sm.transition_to(ConversationStateEnum.LISTENING)

        try:
            # 2. Restore/Create Session & State (< 30 ms SLA)
            restore_start = time.perf_counter()
            session = self.session_manager.restore_session(session_id)
            if not session:
                session = self.session_manager.create_session(user_id="default_user")
                session_id = session.session_id

            session_restore_ms = (time.perf_counter() - restore_start) * 1000.0
            state = self.get_state(session_id)

            # Create new atomic turn
            parent_turn_id = state.history[-1].turn_id if state.history else None
            turn = ConversationTurn(
                session_id=session_id,
                parent_turn_id=parent_turn_id,
                user_text=turn_text_clean,
                created_at=time.time(),
                state=TurnState.STARTED,
            )
            state.history.append(turn)

            # Emit ConversationTurnStarted event
            self.event_bus.emit(
                "ConversationTurnStarted",
                session_id=session_id,
                turn_id=turn.turn_id,
                user_text=turn_text_clean,
            )

            # 3. Transition to THINKING
            sm.transition_to(ConversationStateEnum.THINKING)
            turn.state = TurnState.THINKING
            self.event_bus.emit(
                "ConversationThinking",
                session_id=session_id,
                turn_id=turn.turn_id,
            )

            # 4. Resolve References ("that", "it", "same") (< 20 ms SLA)
            ref_start = time.perf_counter()
            resolved_refs = self.context_tracker.resolve_references(turn_text_clean, state)
            reference_resolution_ms = (time.perf_counter() - ref_start) * 1000.0

            # 5. Track Topic (< 20 ms SLA)
            topic_start = time.perf_counter()
            self.topic_manager.track_topic(turn_text_clean, state)
            topic_tracking_ms = (time.perf_counter() - topic_start) * 1000.0

            # 6. Intent Classification
            has_refs = len(resolved_refs) > 0
            intent_res = self.intent_processor.classify_intent(turn_text_clean, has_resolved_references=has_refs)
            turn.intent = intent_res

            # 7. Update Context & History Trimming
            self.context_tracker.update_context(state, turn_text_clean)
            if len(state.history) > self.max_history_turns:
                state.history = state.history[-self.max_history_turns :]

            # 8. Transition to RESPONDING & Generate Response via IResponseProvider
            sm.transition_to(ConversationStateEnum.RESPONDING)
            turn.state = TurnState.RESPONDING

            response_start = time.perf_counter()
            assistant_response = await self.response_provider.generate_response(turn, session, state)
            response_time_ms = (time.perf_counter() - response_start) * 1000.0

            turn.assistant_response = assistant_response
            turn.response_time_ms = response_time_ms
            turn.state = TurnState.COMPLETED

            # Emit ConversationResponseReady event
            self.event_bus.emit(
                "ConversationResponseReady",
                session_id=session_id,
                turn_id=turn.turn_id,
                assistant_response=assistant_response,
            )

            # 9. Generate Summaries & Continuity Validation
            active_topic_name = state.active_topic.topic_name if state.active_topic else "general"
            short_summary = f"Turn {state.turn_count}: {turn_text_clean[:60]}"
            working_summary = f"Session '{session_id}' turn {state.turn_count} under topic '{active_topic_name}'."
            long_term_summary = f"Dialogue history under '{active_topic_name}' with {state.turn_count} turns."

            summary = ConversationSummary(
                short_summary=short_summary,
                working_summary=working_summary,
                long_term_summary=long_term_summary,
                timestamp=time.time(),
            )

            self.event_bus.emit(
                "ConversationSummarised",
                session_id=session_id,
                summary_id=summary.summary_id,
            )

            validation = self.validator.validate_continuity(state, summary)

            # 10. Metrics & State Transition to WAITING / IDLE
            pipeline_time_ms = (time.perf_counter() - pipeline_start) * 1000.0
            metrics_obj = ContinuityMetrics(
                session_restore_time_ms=session_restore_ms,
                reference_resolution_time_ms=reference_resolution_ms,
                topic_tracking_time_ms=topic_tracking_ms,
                pipeline_time_ms=pipeline_time_ms,
                timestamp=time.time(),
            )

            self.metrics.total_turns += 1
            self.metrics.record_turn_latency(pipeline_time_ms)
            self.metrics.record_response_latency(response_time_ms)
            self.metrics.record_context_size(len(state.history))

            sm.transition_to(ConversationStateEnum.WAITING)
            sm.transition_to(ConversationStateEnum.IDLE)

            # Emit ConversationTurnCompleted & ConversationUpdated events
            self.event_bus.emit(
                "ConversationTurnCompleted",
                session_id=session_id,
                turn_id=turn.turn_id,
                user_text=turn_text_clean,
                assistant_response=assistant_response,
                pipeline_time_ms=pipeline_time_ms,
            )

            self.event_bus.emit(
                "ConversationUpdated",
                session_id=session_id,
                turn_count=state.turn_count,
            )

            log_structured(
                backend_log,
                "INFO",
                f"[ConversationEngine] Processed turn {state.turn_count} for session '{session_id}' in {pipeline_time_ms:.2f} ms",
            )

            return ConversationResult(
                success=True,
                session=session,
                state=state,
                current_turn=turn,
                assistant_response=assistant_response,
                resolved_references=resolved_refs,
                summary=summary,
                validation=validation,
                metrics=metrics_obj,
            )

        except Exception as e:
            sm.transition_to(ConversationStateEnum.ERROR)
            self.metrics.total_errors += 1
            logger.error(f"[ConversationEngine] Exception processing turn for session '{session_id}': {e}")

            self.event_bus.emit(
                "ConversationError",
                session_id=session_id,
                error_message=str(e),
            )

            sm.transition_to(ConversationStateEnum.IDLE)
            return ConversationResult(
                success=False,
                error_message=str(e),
            )


# Global singleton instance
conversation_engine = ConversationContinuityEngine()
