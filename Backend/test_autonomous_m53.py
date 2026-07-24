import sys
import os
import time
import asyncio

# Add Backend root directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from brain.event_bus import event_bus
from autonomous import (
    autonomous_config,
    Goal,
    Task,
    ExecutionPlan,
    GoalStatus,
    ExecutionState,
    ProgressSnapshot,
    progress_tracker,
    ProgressTracker,
)


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_goal_and_task_lifecycles():
    section("1. GOAL & TASK LIFECYCLE STATE MACHINES")

    g = Goal(user_intent="Build React Frontend")
    t1 = Task(goal_id=g.goal_id, name="Npm Install", description="Install node modules", weight=1.0)
    t2 = Task(goal_id=g.goal_id, name="Npm Build", description="Build web bundle", weight=3.0)

    plan = ExecutionPlan(goal_id=g.goal_id, tasks={t1.task_id: t1, t2.task_id: t2})
    snap = progress_tracker.create_progress(g, plan)

    assert snap.goal_id == g.goal_id
    assert snap.overall_progress_pct == 0.0
    assert snap.total_tasks == 2
    assert snap.current_state == GoalStatus.CREATED
    print(f"[PASS] Progress tracking initialized: TotalTasks={snap.total_tasks} | Progress={snap.overall_progress_pct}%")

    # Transition Goal: CREATED -> PLANNING -> IN_PROGRESS
    g.status = GoalStatus.PLANNING
    g.status = GoalStatus.IN_PROGRESS
    snap_start = progress_tracker.get_snapshot(g.goal_id)
    assert snap_start.current_state == GoalStatus.IN_PROGRESS
    print(f"[PASS] Goal state transitioned to IN_PROGRESS.")

    # Task 1: PENDING -> RUNNING -> COMPLETED
    snap_t1_run = progress_tracker.update_goal_task_progress(g.goal_id, t1.task_id, ExecutionState.RUNNING, 0.5)
    assert snap_t1_run.in_progress_tasks == 1
    assert snap_t1_run.overall_progress_pct == 12.5  # (1.0 * 0.5) / 4.0 * 100

    snap_t1_comp = progress_tracker.update_goal_task_progress(g.goal_id, t1.task_id, ExecutionState.COMPLETED)
    assert snap_t1_comp.completed_tasks == 1
    assert snap_t1_comp.overall_progress_pct == 25.0  # 1.0 / 4.0 * 100
    print(f"[PASS] Task 1 completed: OverallProgress={snap_t1_comp.overall_progress_pct}%")


def test_invalid_state_transitions_and_validations():
    section("2. INVALID STATE TRANSITIONS & VALIDATIONS")

    g = Goal(user_intent="Invalid State Test Goal")
    t1 = Task(goal_id=g.goal_id, name="T1", description="T1")
    plan = ExecutionPlan(goal_id=g.goal_id, tasks={t1.task_id: t1})

    progress_tracker.create_progress(g, plan)
    g.status = GoalStatus.IN_PROGRESS

    progress_tracker.update_goal_task_progress(g.goal_id, t1.task_id, ExecutionState.RUNNING)
    progress_tracker.update_goal_task_progress(g.goal_id, t1.task_id, ExecutionState.COMPLETED)

    # 1. Attempt invalid Task transition (COMPLETED -> RUNNING)
    caught_task_err = False
    try:
        progress_tracker.update_goal_task_progress(g.goal_id, t1.task_id, ExecutionState.RUNNING)
    except ValueError as err:
        caught_task_err = True
        assert "Invalid Task state transition" in str(err)
    assert caught_task_err is True
    print(f"[PASS] Invalid Task transition rejected correctly.")

    # 2. Attempt invalid Goal transition (COMPLETED -> PAUSED)
    progress_tracker.complete_goal(g.goal_id)
    caught_goal_err = False
    try:
        progress_tracker.pause_goal(g.goal_id)
    except ValueError as err:
        caught_goal_err = True
        assert "Invalid Goal state transition" in str(err)
    assert caught_goal_err is True
    print(f"[PASS] Invalid Goal transition rejected correctly.")

    # 3. Attempt progress with unknown task_id
    caught_unk_err = False
    try:
        progress_tracker.update_task_progress("non_existent_task_id", ExecutionState.RUNNING)
    except ValueError as err:
        caught_unk_err = True
        assert "Unknown task_id" in str(err)
    assert caught_unk_err is True
    print(f"[PASS] Unknown task ID rejected correctly.")

    # 4. Attempt negative progress delta
    g2 = Goal(user_intent="Delta test")
    t2 = Task(goal_id=g2.goal_id, name="T2", description="T2")
    progress_tracker.create_progress(g2, ExecutionPlan(goal_id=g2.goal_id, tasks={t2.task_id: t2}))
    g2.status = GoalStatus.IN_PROGRESS
    caught_delta_err = False
    try:
        progress_tracker.update_goal_task_progress(g2.goal_id, t2.task_id, ExecutionState.RUNNING, -0.5)
    except ValueError as err:
        caught_delta_err = True
        assert "Invalid progress_delta" in str(err)
    assert caught_delta_err is True
    print(f"[PASS] Negative progress delta rejected correctly.")


def test_eta_and_progress_calculations():
    section("3. ETA & PROGRESS MATH CALCULATIONS")

    g = Goal(user_intent="ETA Math Test Goal")
    t1 = Task(goal_id=g.goal_id, name="Step 1", description="S1", weight=1.0)
    t2 = Task(goal_id=g.goal_id, name="Step 2", description="S2", weight=1.0)
    t3 = Task(goal_id=g.goal_id, name="Step 3", description="S3", weight=1.0)
    plan = ExecutionPlan(goal_id=g.goal_id, tasks={t1.task_id: t1, t2.task_id: t2, t3.task_id: t3})

    progress_tracker.create_progress(g, plan)
    g.status = GoalStatus.IN_PROGRESS

    # Task 1 runs and completes in ~0.1s
    progress_tracker.update_goal_task_progress(g.goal_id, t1.task_id, ExecutionState.RUNNING)
    time.sleep(0.1)
    snap1 = progress_tracker.update_goal_task_progress(g.goal_id, t1.task_id, ExecutionState.COMPLETED)

    assert snap1.overall_progress_pct == 33.33
    assert snap1.estimated_remaining_seconds is not None
    assert snap1.estimated_remaining_seconds > 0.0
    print(f"[PASS] ETA calculated correctly: {snap1.estimated_remaining_seconds}s for 2 remaining tasks.")

    # Task 2 completes
    snap2 = progress_tracker.update_goal_task_progress(g.goal_id, t2.task_id, ExecutionState.COMPLETED)
    assert snap2.overall_progress_pct == 66.67

    # Goal completion sets progress to 100%
    snap_final = progress_tracker.complete_goal(g.goal_id, "All steps finished")
    assert snap_final.overall_progress_pct == 100.0
    assert snap_final.current_state == GoalStatus.COMPLETED
    print(f"[PASS] Final snapshot completed with 100.0% progress.")


def test_pause_resume_cancel_and_events():
    section("4. PAUSE, RESUME, CANCEL & EVENTBUS BROADCASTS")

    captured_events = []
    def capture(event):
        captured_events.append(event.name)

    event_bus.subscribe(autonomous_config.EVENT_PROGRESS_UPDATED, capture)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_PAUSED, capture)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_RESUMED, capture)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_COMPLETED, capture)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_FAILED, capture)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_CANCELLED, capture)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_PROGRESS_CHANGED, capture)

    g = Goal(user_intent="Control Test Goal")
    t1 = Task(goal_id=g.goal_id, name="Control Task", description="C1")
    plan = ExecutionPlan(goal_id=g.goal_id, tasks={t1.task_id: t1})

    progress_tracker.create_progress(g, plan)
    g.status = GoalStatus.IN_PROGRESS

    # Pause Goal
    snap_paused = progress_tracker.pause_goal(g.goal_id)
    assert snap_paused.current_state == GoalStatus.PAUSED
    print(f"[PASS] Goal paused successfully.")

    # Resume Goal
    snap_resumed = progress_tracker.resume_goal(g.goal_id)
    assert snap_resumed.current_state == GoalStatus.IN_PROGRESS
    print(f"[PASS] Goal resumed successfully.")

    # Cancel Goal
    snap_cancelled = progress_tracker.cancel_goal(g.goal_id, "Test cancellation")
    assert snap_cancelled.current_state == GoalStatus.CANCELLED
    print(f"[PASS] Goal cancelled successfully.")

    # Verify EventBus Emissions
    print(f"[PASS] EventBus emissions captured: {captured_events}")
    assert autonomous_config.EVENT_GOAL_PAUSED in captured_events
    assert autonomous_config.EVENT_GOAL_RESUMED in captured_events
    assert autonomous_config.EVENT_GOAL_CANCELLED in captured_events


def test_multiple_concurrent_goals():
    section("5. MULTIPLE CONCURRENT GOALS TRACKING")

    g1 = Goal(user_intent="Concurrent Goal 1")
    g2 = Goal(user_intent="Concurrent Goal 2")

    t1 = Task(goal_id=g1.goal_id, name="G1_T1", description="T1")
    t2 = Task(goal_id=g2.goal_id, name="G2_T1", description="T2")

    progress_tracker.create_progress(g1, ExecutionPlan(goal_id=g1.goal_id, tasks={t1.task_id: t1}))
    progress_tracker.create_progress(g2, ExecutionPlan(goal_id=g2.goal_id, tasks={t2.task_id: t2}))

    g1.status = GoalStatus.IN_PROGRESS
    g2.status = GoalStatus.IN_PROGRESS

    progress_tracker.update_goal_task_progress(g1.goal_id, t1.task_id, ExecutionState.COMPLETED)
    snap1 = progress_tracker.complete_goal(g1.goal_id)
    snap2 = progress_tracker.get_snapshot(g2.goal_id)

    assert snap1.overall_progress_pct == 100.0
    assert snap1.current_state == GoalStatus.COMPLETED
    assert snap2.overall_progress_pct == 0.0
    assert snap2.current_state == GoalStatus.IN_PROGRESS
    print(f"[PASS] Concurrent goals tracked independently without state collision.")


def main():
    test_goal_and_task_lifecycles()
    test_invalid_state_transitions_and_validations()
    test_eta_and_progress_calculations()
    test_pause_resume_cancel_and_events()
    test_multiple_concurrent_goals()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 5.3 CORE AUTONOMOUS TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
