import sys
import os
import time
import asyncio

# Add Backend root directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from brain.event_bus import event_bus
from tools.registry import registry
from autonomous import (
    autonomous_config,
    Goal,
    Task,
    ExecutionPlan,
    ExecutionState,
    TaskResult,
    recovery_engine,
    FailureRecoveryEngine,
    FailureCategory,
    RecoveryStrategy,
    FailureClassification,
    RecoveryDecision,
)


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_failure_classification():
    section("1. FAILURE CLASSIFICATION (10 CATEGORIES)")

    engine = FailureRecoveryEngine()

    test_cases = [
        ("Task execution timed out after 10s", ExecutionState.FAILED, FailureCategory.TIMEOUT),
        ("Permission denied for action", ExecutionState.FAILED, FailureCategory.PERMISSION_DENIED),
        ("Missing required parameter 'path'", ExecutionState.FAILED, FailureCategory.INVALID_ARGUMENTS),
        ("No such file or directory: text.txt", ExecutionState.FAILED, FailureCategory.MISSING_FILE),
        ("Application process terminated unexpectedly", ExecutionState.FAILED, FailureCategory.APPLICATION_CRASH),
        ("Network HTTP connection lost", ExecutionState.FAILED, FailureCategory.NETWORK_ERROR),
        ("User cancelled action", ExecutionState.CANCELLED, FailureCategory.USER_CANCELLED),
        ("Tool output format was unexpected", ExecutionState.FAILED, FailureCategory.UNEXPECTED_OUTPUT),
        ("Tool execution failed with zero exit", ExecutionState.FAILED, FailureCategory.TOOL_EXECUTION_ERROR),
        ("Something unknown went wrong", ExecutionState.FAILED, FailureCategory.UNKNOWN_ERROR),
    ]

    for err_text, status, expected_cat in test_cases:
        cls = engine.classify_failure(err_text, status)
        assert cls.category == expected_cat
        assert isinstance(cls.severity, str)
        print(f"[PASS] Classified '{err_text[:30]}...' -> Category={cls.category.value} | Strategy={cls.recommended_strategy.value}")


async def test_retry_policy_and_limits():
    section("2. RETRY POLICY & EXPONENTIAL BACKOFF LIMITS")

    engine = FailureRecoveryEngine()
    g = Goal(user_intent="Retry Test Goal")
    t = Task(goal_id=g.goal_id, name="Flaky Task", description="Flaky step", max_retries=2)
    plan = ExecutionPlan(goal_id=g.goal_id, tasks={t.task_id: t})

    # Retry 1
    res1 = TaskResult(task_id=t.task_id, status=ExecutionState.FAILED, error="Task execution timed out")
    dec1 = await engine.evaluate_and_recover(t, res1, plan, g)
    assert dec1.strategy == RecoveryStrategy.RETRY
    assert dec1.backoff_delay_seconds == 0.5  # 0.5 * 2^0
    print(f"[PASS] Retry 1 scheduled: Backoff={dec1.backoff_delay_seconds}s")

    # Retry 2
    dec2 = await engine.evaluate_and_recover(t, res1, plan, g)
    assert dec2.strategy == RecoveryStrategy.RETRY
    assert dec2.backoff_delay_seconds == 1.0  # 0.5 * 2^1
    print(f"[PASS] Retry 2 scheduled: Backoff={dec2.backoff_delay_seconds}s")

    # Retries Exhausted -> Alternative Tool / Replan / Escalation
    dec3 = await engine.evaluate_and_recover(t, res1, plan, g)
    assert dec3.strategy in (RecoveryStrategy.ALTERNATIVE_TOOL, RecoveryStrategy.DYNAMIC_REPLAN, RecoveryStrategy.USER_ESCALATION)
    print(f"[PASS] Retries exhausted: Transitioned to strategy '{dec3.strategy.value}'.")


async def test_alternative_tool_selection():
    section("3. ALTERNATIVE TOOL SELECTION & MISSING CANDIDATE FALLBACK")

    engine = FailureRecoveryEngine()
    g = Goal(user_intent="Alt Tool Test Goal")

    # Register two tools for testing
    @registry.register(name="primary_browser_tool", description="Primary tool", parameters={})
    def primary(): return "Primary"

    @registry.register(name="secondary_browser_tool", description="Secondary tool", parameters={})
    def secondary(): return "Secondary"

    t = Task(goal_id=g.goal_id, name="Open Tab", description="Open browser", suggested_tool="primary_browser_tool", max_retries=0)
    plan = ExecutionPlan(goal_id=g.goal_id, tasks={t.task_id: t})
    res = TaskResult(task_id=t.task_id, status=ExecutionState.FAILED, error="Invalid parameter passed")

    dec = await engine.evaluate_and_recover(t, res, plan, g)
    assert dec.strategy == RecoveryStrategy.ALTERNATIVE_TOOL
    assert dec.alternative_tool is not None
    assert dec.alternative_tool != "primary_browser_tool"
    print(f"[PASS] Alternative tool selected: '{dec.alternative_tool}'")


async def test_dynamic_replanning_and_user_escalation():
    section("4. DYNAMIC REPLANNING & USER ESCALATION")

    engine = FailureRecoveryEngine()
    g = Goal(user_intent="Replan & Escalate Goal")

    # 1. Missing file failure -> Dynamic Replan
    t_missing = Task(goal_id=g.goal_id, name="Read Config", description="Read missing file", suggested_tool="unknown_tool", max_retries=0)
    plan = ExecutionPlan(goal_id=g.goal_id, tasks={t_missing.task_id: t_missing})
    res_missing = TaskResult(task_id=t_missing.task_id, status=ExecutionState.FAILED, error="No such file or directory: missing.txt")

    dec_replan = await engine.evaluate_and_recover(t_missing, res_missing, plan, g)
    assert dec_replan.strategy == RecoveryStrategy.DYNAMIC_REPLAN
    assert len(dec_replan.replacement_tasks) >= 1
    print(f"[PASS] Dynamic replan generated {len(dec_replan.replacement_tasks)} replacement tasks.")

    # 2. Permission Denied -> User Escalation
    t_perm = Task(goal_id=g.goal_id, name="Delete Folder", description="Delete system folder", suggested_tool="fs_delete", max_retries=0)
    res_perm = TaskResult(task_id=t_perm.task_id, status=ExecutionState.FAILED, error="Permission denied for action")

    dec_esc = await engine.evaluate_and_recover(t_perm, res_perm, plan, g)
    assert dec_esc.strategy == RecoveryStrategy.USER_ESCALATION
    assert dec_esc.escalation_details is not None
    print(f"[PASS] User escalation triggered for permission restriction.")


async def test_infinite_recovery_prevention_and_events():
    section("5. INFINITE RECOVERY PREVENTION & EVENTBUS BROADCASTS")

    captured_events = []
    def capture(event):
        captured_events.append(event.name)

    event_bus.subscribe(autonomous_config.EVENT_RECOVERY_STARTED, capture)
    event_bus.subscribe(autonomous_config.EVENT_RECOVERY_RETRY_SCHEDULED, capture)
    event_bus.subscribe(autonomous_config.EVENT_RECOVERY_ALTERNATIVE_TOOL, capture)
    event_bus.subscribe(autonomous_config.EVENT_RECOVERY_REPLANNED, capture)
    event_bus.subscribe(autonomous_config.EVENT_RECOVERY_ESCALATED, capture)

    engine = FailureRecoveryEngine()
    g = Goal(user_intent="Infinite Prevention Goal")
    t = Task(goal_id=g.goal_id, name="Stubborn Task", description="Stubborn task", max_retries=1)
    plan = ExecutionPlan(goal_id=g.goal_id, tasks={t.task_id: t})
    res = TaskResult(task_id=t.task_id, status=ExecutionState.FAILED, error="Missing file missing.txt")

    # Exceed retry and replan depth limits
    engine._retry_counts[t.task_id] = 10
    engine._replan_depths[g.goal_id] = 10

    dec = await engine.evaluate_and_recover(t, res, plan, g)
    assert dec.strategy == RecoveryStrategy.USER_ESCALATION
    assert "exhausted" in dec.reason.lower()
    print(f"[PASS] Infinite recovery loop prevented by limit guards: Reason='{dec.reason}'")

    print(f"[PASS] EventBus emissions captured: {captured_events}")
    assert autonomous_config.EVENT_RECOVERY_STARTED in captured_events
    assert autonomous_config.EVENT_RECOVERY_ESCALATED in captured_events


async def main():
    test_failure_classification()
    await test_retry_policy_and_limits()
    await test_alternative_tool_selection()
    await test_dynamic_replanning_and_user_escalation()
    await test_infinite_recovery_prevention_and_events()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 5.4 CORE AUTONOMOUS TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
