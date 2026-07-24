import sys
import os
import asyncio

# Ensure Backend directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from brain.event_bus import event_bus
from autonomous import (
    autonomous_config,
    GoalStatus,
    ExecutionState,
    Task,
    Goal,
    ExecutionPlan,
    TaskResult,
    RecoveryAttempt,
    ProgressSnapshot,
    WorkflowCheckpoint,
    IGoalManager,
    ITaskPlanner,
    goal_manager,
    GoalManager,
    task_planner,
    TaskPlanner,
)


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_schema_and_models():
    section("1. DATA MODELS & SCHEMA VALIDATION")

    # 1. Goal model
    g = Goal(user_intent="Organize my Downloads folder")
    assert g.goal_id.startswith("goal_")
    assert g.status == GoalStatus.CREATED
    assert isinstance(g.created_at, float)
    print(f"[PASS] Goal model validated: ID={g.goal_id} | Status={g.status.value}")

    # 2. Task model
    t = Task(goal_id=g.goal_id, name="List Files", description="Scans target folder", suggested_tool="fs_list_directory")
    assert t.task_id.startswith("task_")
    assert t.goal_id == g.goal_id
    assert t.suggested_tool == "fs_list_directory"
    print(f"[PASS] Task model validated: ID={t.task_id} | Name='{t.name}'")

    # 3. ExecutionPlan model
    plan = ExecutionPlan(goal_id=g.goal_id, tasks={t.task_id: t}, dag_edges={t.task_id: []})
    assert plan.plan_id.startswith("plan_")
    assert len(plan.tasks) == 1
    print(f"[PASS] ExecutionPlan model validated: PlanID={plan.plan_id}")

    # 4. TaskResult model
    res = TaskResult(task_id=t.task_id, status=ExecutionState.COMPLETED, output={"files": 12}, execution_time_seconds=0.45)
    assert res.status == ExecutionState.COMPLETED
    assert res.output == {"files": 12}
    print(f"[PASS] TaskResult model validated: Status={res.status.value}")

    # 5. ProgressSnapshot & Checkpoint models
    snap = ProgressSnapshot(goal_id=g.goal_id, overall_progress_pct=50.0, total_tasks=2, completed_tasks=1)
    assert snap.overall_progress_pct == 50.0

    chk = WorkflowCheckpoint(workflow_id="wf_123", goal_id=g.goal_id, plan=plan)
    assert chk.checkpoint_id.startswith("chk_")
    print(f"[PASS] ProgressSnapshot & WorkflowCheckpoint validated.")


async def test_goal_manager_lifecycle():
    section("2. GOAL MANAGER LIFECYCLE & EVENTBUS INTEGRATION")

    captured_events = []
    def event_handler(event):
        captured_events.append(event.name)

    event_bus.subscribe(autonomous_config.EVENT_GOAL_CREATED, event_handler)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_STARTED, event_handler)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_COMPLETED, event_handler)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_CANCELLED, event_handler)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_FAILED, event_handler)
    event_bus.subscribe(autonomous_config.EVENT_EXECUTION_PAUSED, event_handler)
    event_bus.subscribe(autonomous_config.EVENT_EXECUTION_RESUMED, event_handler)

    # 1. Create Goal
    goal = await goal_manager.create_goal("Build React application", metadata={"priority": "high"})
    assert isinstance(goal_manager, IGoalManager)
    assert goal.status == GoalStatus.CREATED
    print(f"[PASS] create_goal succeeded: ID={goal.goal_id}")

    # 2. Start Goal
    started = await goal_manager.start_goal(goal.goal_id)
    assert started is True
    fetched = await goal_manager.get_goal_status(goal.goal_id)
    assert fetched.status == GoalStatus.IN_PROGRESS
    print(f"[PASS] start_goal succeeded: Status={fetched.status.value}")

    # 3. Pause & Resume Goal
    paused = await goal_manager.pause_goal(goal.goal_id)
    assert paused is True
    assert (await goal_manager.get_goal_status(goal.goal_id)).status == GoalStatus.PAUSED

    resumed = await goal_manager.resume_goal(goal.goal_id)
    assert resumed is True
    assert (await goal_manager.get_goal_status(goal.goal_id)).status == GoalStatus.IN_PROGRESS
    print(f"[PASS] pause_goal and resume_goal succeeded.")

    # 4. Complete Goal
    completed = await goal_manager.complete_goal(goal.goal_id, summary="React app built successfully.")
    assert completed is True
    assert (await goal_manager.get_goal_status(goal.goal_id)).status == GoalStatus.COMPLETED
    print(f"[PASS] complete_goal succeeded: Summary='{fetched.summary_result}'")

    # 5. List Goals
    all_goals = await goal_manager.list_goals()
    assert len(all_goals) >= 1
    completed_goals = await goal_manager.list_goals(status="completed")
    assert len(completed_goals) >= 1
    print(f"[PASS] list_goals succeeded: Count={len(all_goals)}")

    # 6. Cancellation check on new goal
    g2 = await goal_manager.create_goal("Temporary Goal")
    cancelled = await goal_manager.cancel_goal(g2.goal_id, reason="User stop request")
    assert cancelled is True
    assert (await goal_manager.get_goal_status(g2.goal_id)).status == GoalStatus.CANCELLED
    print(f"[PASS] cancel_goal succeeded.")

    print(f"[PASS] EventBus emissions captured: {captured_events}")
    assert autonomous_config.EVENT_GOAL_CREATED in captured_events
    assert autonomous_config.EVENT_GOAL_STARTED in captured_events
    assert autonomous_config.EVENT_GOAL_COMPLETED in captured_events
    assert autonomous_config.EVENT_GOAL_CANCELLED in captured_events


async def test_task_planner_decomposition():
    section("3. TASK PLANNER DECOMPOSITION & REPLANNING")

    captured_task_events = []
    def task_event_handler(event):
        captured_task_events.append(event.name)

    event_bus.subscribe(autonomous_config.EVENT_TASK_CREATED, task_event_handler)

    # 1. Test "Organize Downloads" goal decomposition
    g_org = Goal(user_intent="Organize my Downloads folder")
    tasks_org = await task_planner.plan_tasks(g_org)
    assert isinstance(task_planner, ITaskPlanner)
    assert len(tasks_org) == 3
    assert tasks_org[0].name == "Scan Folder"
    assert tasks_org[1].dependencies == [tasks_org[0].task_id]
    assert tasks_org[2].dependencies == [tasks_org[1].task_id]
    print(f"[PASS] 'Organize Downloads' plan decomposed into {len(tasks_org)} sequential tasks.")

    # 2. Test "Build React project" goal decomposition
    g_build = Goal(user_intent="Build React project in D:/App")
    tasks_build = await task_planner.plan_tasks(g_build)
    assert len(tasks_build) == 3
    assert tasks_build[1].suggested_tool == "terminal_execute"
    print(f"[PASS] 'Build React project' plan decomposed into {len(tasks_build)} tasks.")

    # 3. Test Subgraph Replanning
    failed_task = tasks_org[1]
    replanned = await task_planner.replan_subgraph(g_org, failed_task, "File access permission denied")
    assert len(replanned) == 1
    assert replanned[0].name.startswith("Recover:")
    assert replanned[0].dependencies == failed_task.dependencies
    print(f"[PASS] replan_subgraph generated valid recovery task.")

    assert autonomous_config.EVENT_TASK_CREATED in captured_task_events
    print(f"[PASS] TaskCreated events captured cleanly.")


async def main():
    test_schema_and_models()
    await test_goal_manager_lifecycle()
    await test_task_planner_decomposition()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 5.1 CORE AUTONOMOUS TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
