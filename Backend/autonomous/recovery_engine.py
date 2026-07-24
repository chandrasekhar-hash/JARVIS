import re
import time
from enum import Enum
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log
from autonomous.models import Task, TaskResult, ExecutionPlan, Goal, RecoveryAttempt, ExecutionState
from autonomous.interfaces import IFailureRecoveryEngine
from autonomous.config import autonomous_config
from autonomous.tool_selector import tool_selector
from autonomous.task_planner import task_planner


class FailureCategory(str, Enum):
    TOOL_EXECUTION_ERROR = "tool_execution_error"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    INVALID_ARGUMENTS = "invalid_arguments"
    APPLICATION_CRASH = "application_crash"
    MISSING_FILE = "missing_file"
    NETWORK_ERROR = "network_error"
    USER_CANCELLED = "user_cancelled"
    UNEXPECTED_OUTPUT = "unexpected_output"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    ALTERNATIVE_TOOL = "alternative_tool"
    DYNAMIC_REPLAN = "dynamic_replan"
    USER_ESCALATION = "user_escalation"
    ABORT_GOAL = "abort_goal"


class FailureClassification(BaseModel):
    category: FailureCategory
    severity: str  # "low" | "medium" | "high" | "critical"
    recoverable: bool
    recommended_strategy: RecoveryStrategy
    description: str


class RecoveryDecision(BaseModel):
    attempt_id: str
    task_id: str
    strategy: RecoveryStrategy
    reason: str
    confidence: float = 1.0
    estimated_success_probability: float = 0.8
    backoff_delay_seconds: float = 0.0
    alternative_tool: Optional[str] = None
    replacement_tasks: List[Task] = Field(default_factory=list)
    escalation_details: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)


class FailureRecoveryEngine(IFailureRecoveryEngine):
    """Subsystem responsible for classifying execution failures and selecting optimal recovery strategies."""

    def __init__(self):
        # task_id -> retry count
        self._retry_counts: Dict[str, int] = {}
        # goal_id -> replan depth
        self._replan_depths: Dict[str, int] = {}
        # task_id -> set of attempted alt tools
        self._attempted_alt_tools: Dict[str, Set[str]] = {}

    def classify_failure(self, error_msg: Optional[str], status: ExecutionState) -> FailureClassification:
        """Analyzes error messages and execution status to classify failure category and severity."""
        err = (error_msg or "").lower()

        if status == ExecutionState.CANCELLED or "cancelled" in err:
            return FailureClassification(
                category=FailureCategory.USER_CANCELLED,
                severity="low",
                recoverable=False,
                recommended_strategy=RecoveryStrategy.ABORT_GOAL,
                description="Task execution was cancelled by user request."
            )

        if "timed out" in err or "timeout" in err:
            return FailureClassification(
                category=FailureCategory.TIMEOUT,
                severity="medium",
                recoverable=True,
                recommended_strategy=RecoveryStrategy.RETRY,
                description="Execution timed out before completion."
            )

        if "permission" in err or "denied" in err or "confirmation" in err or "approval" in err:
            return FailureClassification(
                category=FailureCategory.PERMISSION_DENIED,
                severity="high",
                recoverable=True,
                recommended_strategy=RecoveryStrategy.USER_ESCALATION,
                description="Operation requires explicit user confirmation or permission approval."
            )

        if "missing required parameter" in err or "invalid parameter" in err or "invalid argument" in err or "argument validation failed" in err:
            return FailureClassification(
                category=FailureCategory.INVALID_ARGUMENTS,
                severity="medium",
                recoverable=True,
                recommended_strategy=RecoveryStrategy.ALTERNATIVE_TOOL,
                description="Tool argument validation failed."
            )

        if "missing" in err or "not found" in err or "no such file" in err:
            return FailureClassification(
                category=FailureCategory.MISSING_FILE,
                severity="medium",
                recoverable=True,
                recommended_strategy=RecoveryStrategy.DYNAMIC_REPLAN,
                description="Target file or directory path was missing."
            )

        if "crash" in err or "closed unexpectedly" in err or "process terminated" in err:
            return FailureClassification(
                category=FailureCategory.APPLICATION_CRASH,
                severity="high",
                recoverable=True,
                recommended_strategy=RecoveryStrategy.ALTERNATIVE_TOOL,
                description="Desktop application or process crashed unexpectedly."
            )

        if "network" in err or "connection" in err or "http" in err or "unreachable" in err:
            return FailureClassification(
                category=FailureCategory.NETWORK_ERROR,
                severity="medium",
                recoverable=True,
                recommended_strategy=RecoveryStrategy.RETRY,
                description="Network connectivity or remote endpoint error."
            )

        if "unexpected" in err or "malformed" in err or "parse error" in err:
            return FailureClassification(
                category=FailureCategory.UNEXPECTED_OUTPUT,
                severity="medium",
                recoverable=True,
                recommended_strategy=RecoveryStrategy.DYNAMIC_REPLAN,
                description="Tool output format was unexpected or invalid."
            )

        if "tool" in err and "error" in err:
            return FailureClassification(
                category=FailureCategory.TOOL_EXECUTION_ERROR,
                severity="medium",
                recoverable=True,
                recommended_strategy=RecoveryStrategy.RETRY,
                description="Tool execution raised a runtime error."
            )

        if "failed" in err or "error" in err:
            return FailureClassification(
                category=FailureCategory.TOOL_EXECUTION_ERROR,
                severity="medium",
                recoverable=True,
                recommended_strategy=RecoveryStrategy.RETRY,
                description="General task execution error."
            )

        return FailureClassification(
            category=FailureCategory.UNKNOWN_ERROR,
            severity="medium",
            recoverable=True,
            recommended_strategy=RecoveryStrategy.RETRY,
            description="Unclassified runtime exception."
        )

    def calculate_backoff(self, retry_count: int) -> float:
        """Calculates exponential backoff delay: 0.5s * 2^(retry_count)."""
        return round(0.5 * (2 ** retry_count), 2)

    async def evaluate_and_recover(
        self, 
        task: Task, 
        result: TaskResult, 
        plan: ExecutionPlan,
        goal: Optional[Goal] = None
    ) -> RecoveryDecision:
        """
        Evaluates a failed task result and formulates a recovery decision.
        Never executes the recovery action directly.
        """
        task_id = task.task_id
        goal_id = task.goal_id
        current_retries = self._retry_counts.get(task_id, 0)
        current_replans = self._replan_depths.get(goal_id, 0)
        max_retries = task.max_retries or autonomous_config.MAX_TASK_RETRIES
        max_replan = autonomous_config.MAX_REPLAN_DEPTH

        classification = self.classify_failure(result.error, result.status)
        log_structured(
            backend_log, 
            "WARNING", 
            f"[FailureRecoveryEngine] Evaluating failure for Task {task_id}: {classification.category.value} ({classification.severity})"
        )

        event_bus.emit(
            autonomous_config.EVENT_RECOVERY_STARTED,
            task_id=task_id,
            category=classification.category.value,
            severity=classification.severity
        )

        # 1. Non-recoverable or User Cancelled -> Abort Goal
        if not classification.recoverable or classification.category == FailureCategory.USER_CANCELLED:
            decision = RecoveryDecision(
                attempt_id=f"rec_{task_id[:8]}",
                task_id=task_id,
                strategy=RecoveryStrategy.ABORT_GOAL,
                reason=classification.description,
                confidence=1.0,
                estimated_success_probability=0.0
            )
            event_bus.emit(autonomous_config.EVENT_RECOVERY_FAILED, task_id=task_id, unrecoverable_reason=decision.reason)
            return decision

        # 2. Permission Denied -> User Escalation
        if classification.category == FailureCategory.PERMISSION_DENIED:
            decision = RecoveryDecision(
                attempt_id=f"rec_{task_id[:8]}",
                task_id=task_id,
                strategy=RecoveryStrategy.USER_ESCALATION,
                reason="Permission required before executing requested tool action.",
                confidence=0.9,
                estimated_success_probability=0.95,
                escalation_details={"task_name": task.name, "tool": task.suggested_tool, "args": task.input_params}
            )
            event_bus.emit(autonomous_config.EVENT_RECOVERY_ESCALATED, task_id=task_id, reason=decision.reason)
            return decision

        # 3. Infinite Recovery Guard (If both retries AND replan depth limits are exhausted)
        if current_retries >= max_retries and current_replans >= max_replan:
            decision = RecoveryDecision(
                attempt_id=f"rec_{task_id[:8]}",
                task_id=task_id,
                strategy=RecoveryStrategy.USER_ESCALATION,
                reason=f"Recovery attempts exhausted for task '{task.name}' (Retries: {current_retries}/{max_retries}, Replans: {current_replans}/{max_replan}).",
                confidence=0.95,
                estimated_success_probability=0.5,
                escalation_details={"task_id": task_id, "error": result.error, "exhausted": True}
            )
            event_bus.emit(autonomous_config.EVENT_RECOVERY_ESCALATED, task_id=task_id, reason=decision.reason)
            return decision

        # 4. Retry Strategy Check
        if current_retries < max_retries and classification.recommended_strategy == RecoveryStrategy.RETRY:
            self._retry_counts[task_id] = current_retries + 1
            backoff = self.calculate_backoff(current_retries)
            decision = RecoveryDecision(
                attempt_id=f"rec_{task_id[:8]}",
                task_id=task_id,
                strategy=RecoveryStrategy.RETRY,
                reason=f"Attempting retry {current_retries + 1}/{max_retries} with {backoff}s backoff.",
                confidence=0.85,
                estimated_success_probability=0.7,
                backoff_delay_seconds=backoff
            )
            event_bus.emit(
                autonomous_config.EVENT_RECOVERY_RETRY_SCHEDULED,
                task_id=task_id,
                attempt=current_retries + 1,
                backoff=backoff
            )
            return decision

        # 5. Alternative Tool Check
        available_tools = tool_selector.discover_tools() if hasattr(tool_selector, "discover_tools") else []
        attempted = self._attempted_alt_tools.get(task_id, set())
        alt_candidates = [t for t in available_tools if t != task.suggested_tool and t not in attempted]

        if alt_candidates and (
            classification.recommended_strategy == RecoveryStrategy.ALTERNATIVE_TOOL or 
            classification.category in (FailureCategory.INVALID_ARGUMENTS, FailureCategory.APPLICATION_CRASH)
        ):
            chosen_alt = alt_candidates[0]
            if task_id not in self._attempted_alt_tools:
                self._attempted_alt_tools[task_id] = set()
            self._attempted_alt_tools[task_id].add(chosen_alt)

            decision = RecoveryDecision(
                attempt_id=f"rec_{task_id[:8]}",
                task_id=task_id,
                strategy=RecoveryStrategy.ALTERNATIVE_TOOL,
                reason=f"Switching tool from '{task.suggested_tool}' to alternative candidate '{chosen_alt}'.",
                confidence=0.8,
                estimated_success_probability=0.75,
                alternative_tool=chosen_alt
            )
            event_bus.emit(autonomous_config.EVENT_RECOVERY_ALTERNATIVE_TOOL, task_id=task_id, alternative_tool=chosen_alt)
            return decision

        # 6. Dynamic Replanning Check
        if current_replans < max_replan:
            self._replan_depths[goal_id] = current_replans + 1
            target_goal = goal or Goal(goal_id=goal_id, user_intent=task.description)
            replacement_tasks = await task_planner.replan_subgraph(target_goal, task, result.error or "Unknown task error")

            decision = RecoveryDecision(
                attempt_id=f"rec_{task_id[:8]}",
                task_id=task_id,
                strategy=RecoveryStrategy.DYNAMIC_REPLAN,
                reason=f"Generated replacement subgraph tasks (Replan depth {current_replans + 1}/{max_replan}).",
                confidence=0.85,
                estimated_success_probability=0.8,
                replacement_tasks=replacement_tasks
            )
            event_bus.emit(autonomous_config.EVENT_RECOVERY_REPLANNED, task_id=task_id, new_tasks_count=len(replacement_tasks))
            return decision

        # 7. Fallback Escalation to User
        decision = RecoveryDecision(
            attempt_id=f"rec_{task_id[:8]}",
            task_id=task_id,
            strategy=RecoveryStrategy.USER_ESCALATION,
            reason=f"Recovery attempts exhausted for task '{task.name}' (Retries: {current_retries}, Replans: {current_replans}).",
            confidence=0.95,
            estimated_success_probability=0.5,
            escalation_details={"task_id": task_id, "error": result.error, "exhausted": True}
        )
        event_bus.emit(autonomous_config.EVENT_RECOVERY_ESCALATED, task_id=task_id, reason=decision.reason)
        return decision

    def reset_task_recovery_state(self, task_id: str) -> None:
        """Resets retry counter for a task upon successful recovery."""
        self._retry_counts.pop(task_id, None)
        self._attempted_alt_tools.pop(task_id, None)


recovery_engine = FailureRecoveryEngine()
