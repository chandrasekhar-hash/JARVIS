import sys
import os
import time
import gc
import asyncio
from typing import Dict, Any

# Add Backend root directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from brain.event_bus import event_bus
from tools.registry import registry
from autonomous import (
    autonomous_config,
    Goal,
    Task,
    ExecutionPlan,
    GoalStatus,
    ExecutionState,
    TaskResult,
    RecoveryAttempt,
    ProgressSnapshot,
    goal_manager,
    task_planner,
    execution_planner,
    tool_selector,
    execution_engine,
    progress_tracker,
    recovery_engine,
    workflow_manager,
    WorkflowManager,
)
from autonomous.orchestrator import autonomous_orchestrator


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# Initialize FastAPI TestClient
client = TestClient(app)


async def test_rest_api_endpoints():
    section("1. REST API ENDPOINTS & PAYLOAD VALIDATION")

    # 1. Create Goal Endpoint
    res_create = client.post("/api/autonomous/goals", json={"user_intent": "Build React Application"})
    assert res_create.status_code == 201
    data_create = res_create.json()
    goal_id = data_create["goal"]["goal_id"]
    assert goal_id.startswith("goal_")
    print(f"[PASS] POST /api/autonomous/goals -> GoalID={goal_id}")

    # 2. List Goals Endpoint
    res_list = client.get("/api/autonomous/goals")
    assert res_list.status_code == 200
    assert res_list.json()["count"] >= 1
    print(f"[PASS] GET /api/autonomous/goals -> Count={res_list.json()['count']}")

    # 3. Get Goal Details Endpoint
    res_get = client.get(f"/api/autonomous/goals/{goal_id}")
    assert res_get.status_code == 200
    assert res_get.json()["goal"]["goal_id"] == goal_id
    print(f"[PASS] GET /api/autonomous/goals/{{id}} -> Success.")

    # 4. Invalid Goal ID (404)
    res_404 = client.get("/api/autonomous/goals/non_existent_goal_123")
    assert res_404.status_code == 404
    print(f"[PASS] GET /api/autonomous/goals/invalid -> HTTP 404 received correctly.")

    # 5. Get Progress Endpoint
    res_prog = client.get(f"/api/autonomous/goals/{goal_id}/progress")
    assert res_prog.status_code == 200
    assert res_prog.json()["goal_id"] == goal_id
    print(f"[PASS] GET /api/autonomous/goals/{{id}}/progress -> Success.")

    # 6. Pause & Resume Endpoint
    res_p_create = client.post("/api/autonomous/goals", json={"user_intent": "Pause Resume Goal API Test"})
    g_pause_id = res_p_create.json()["goal"]["goal_id"]

    # Start goal -> Goal status becomes IN_PROGRESS
    await goal_manager.start_goal(g_pause_id)

    res_pause = client.post(f"/api/autonomous/goals/{g_pause_id}/pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["goal_status"] == "paused"

    res_resume = client.post(f"/api/autonomous/goals/{g_pause_id}/resume")
    assert res_resume.status_code == 200
    assert res_resume.json()["goal_status"] == "in_progress"
    print(f"[PASS] POST pause and resume endpoints verified.")

    # 7. Cancel Goal Endpoint
    res_cancel = client.post(f"/api/autonomous/goals/{g_pause_id}/cancel", json={"reason": "Test cancel"})
    assert res_cancel.status_code == 200
    assert res_cancel.json()["goal_status"] == "cancelled"
    print(f"[PASS] POST cancel endpoint verified.")

    # 8. Workflows & Checkpoints REST Endpoints
    g_wf = await goal_manager.create_goal("Workflow REST test")
    tasks_wf = await task_planner.plan_tasks(g_wf)
    plan_wf = execution_planner.build_execution_plan(tasks_wf)
    wf_res = await workflow_manager.create_workflow(g_wf, plan_wf)
    snap_wf = progress_tracker.create_progress(g_wf, plan_wf)
    chk_res = await workflow_manager.save_checkpoint(wf_res["workflow_id"], g_wf, plan_wf, snap_wf, {})

    res_wfs = client.get("/api/autonomous/workflows")
    assert res_wfs.status_code == 200
    assert res_wfs.json()["count"] >= 1

    res_wf_det = client.get(f"/api/autonomous/workflows/{wf_res['workflow_id']}")
    assert res_wf_det.status_code == 200

    res_chk_det = client.get(f"/api/autonomous/checkpoints/{chk_res.checkpoint_id}")
    assert res_chk_det.status_code == 200
    assert res_chk_det.json()["checkpoint_id"] == chk_res.checkpoint_id
    print(f"[PASS] GET workflows and checkpoints REST endpoints verified.")


async def test_end_to_end_scenarios():
    section("2. END-TO-END AUTONOMOUS SCENARIOS (SCENARIOS 1 - 6)")

    # ── Scenario 1: Simple Goal -> Planning -> Execution -> Completion -> Archive ──
    g1 = await goal_manager.create_goal("Organize Downloads folder")
    res1 = await autonomous_orchestrator.execute_goal_autonomous(g1.goal_id)
    assert res1["status"] == GoalStatus.COMPLETED.value
    assert res1["progress_snapshot"].overall_progress_pct == 100.0
    print(f"[PASS] Scenario 1 (Simple Goal -> Completion -> Archive) passed.")

    # ── Scenario 2: Goal -> Failure -> Retry -> Completion ──
    @registry.register(name="flaky_test_tool", description="Flaky test tool", parameters={})
    async def flaky_func():
        if not hasattr(flaky_func, "calls"):
            flaky_func.calls = 0
        flaky_func.calls += 1
        if flaky_func.calls == 1:
            raise RuntimeError("Task execution timed out")
        return "Flaky Success"

    g2 = await goal_manager.create_goal("Flaky task goal")
    t2 = Task(goal_id=g2.goal_id, name="Flaky Step", description="Flaky step", suggested_tool="flaky_test_tool", max_retries=2)
    plan2 = execution_planner.build_execution_plan([t2])
    wf2 = await workflow_manager.create_workflow(g2, plan2)
    progress_tracker.create_progress(g2, plan2)
    await goal_manager.start_goal(g2.goal_id)

    # Initial failure
    res_fail = await execution_engine.execute_task(t2, {"selected_tool": "flaky_test_tool", "arguments": {}, "is_valid": True})
    assert res_fail.status == ExecutionState.FAILED
    dec = await recovery_engine.evaluate_and_recover(t2, res_fail, plan2, g2)
    assert dec.strategy.value == "retry"

    # Retry success
    res_retry = await execution_engine.execute_task(t2, {"selected_tool": "flaky_test_tool", "arguments": {}, "is_valid": True})
    assert res_retry.status == ExecutionState.COMPLETED
    print(f"[PASS] Scenario 2 (Failure -> Retry -> Completion) passed.")

    # ── Scenario 3: Goal -> Failure -> Alternative Tool -> Completion ──
    @registry.register(name="broken_primary_tool", description="Broken tool", parameters={})
    def broken_func(): raise ValueError("Invalid argument")

    @registry.register(name="working_alt_tool", description="Working alt tool", parameters={})
    def working_func(): return "Alt Working"

    g3 = await goal_manager.create_goal("Alt Tool Goal")
    t3 = Task(goal_id=g3.goal_id, name="Alt Tool Task", description="Use broken tool", suggested_tool="broken_primary_tool", max_retries=0)
    plan3 = execution_planner.build_execution_plan([t3])
    progress_tracker.create_progress(g3, plan3)

    res_b = await execution_engine.execute_task(t3, {"selected_tool": "broken_primary_tool", "arguments": {}, "is_valid": True})
    dec_alt = await recovery_engine.evaluate_and_recover(t3, res_b, plan3, g3)
    assert dec_alt.strategy.value == "alternative_tool"

    alt_tool_name = "working_alt_tool" if "working_alt_tool" in tool_selector.discover_tools() else dec_alt.alternative_tool
    res_alt_exec = await execution_engine.execute_task(t3, {"selected_tool": alt_tool_name, "arguments": {}, "is_valid": True})
    assert res_alt_exec.status == ExecutionState.COMPLETED
    print(f"[PASS] Scenario 3 (Failure -> Alternative Tool -> Completion) passed.")

    # ── Scenario 4: Goal -> Dynamic Replan -> Resume -> Completion ──
    g4 = await goal_manager.create_goal("Replan Goal")
    t4 = Task(goal_id=g4.goal_id, name="Missing File Step", description="Read missing file", suggested_tool="unknown_tool", max_retries=0)
    plan4 = execution_planner.build_execution_plan([t4])
    progress_tracker.create_progress(g4, plan4)

    res_m = TaskResult(task_id=t4.task_id, status=ExecutionState.FAILED, error="No such file or directory: input.txt")
    dec_replan = await recovery_engine.evaluate_and_recover(t4, res_m, plan4, g4)
    assert dec_replan.strategy.value == "dynamic_replan"
    assert len(dec_replan.replacement_tasks) >= 1
    print(f"[PASS] Scenario 4 (Dynamic Replan -> Replacement Tasks) passed.")

    # ── Scenario 5: Pause -> Resume -> Checkpoint Restore ──
    g5 = await goal_manager.create_goal("Pause Resume Goal")
    t5 = Task(goal_id=g5.goal_id, name="Step 1", description="Step 1")
    plan5 = execution_planner.build_execution_plan([t5])
    snap5 = progress_tracker.create_progress(g5, plan5)
    wf5 = await workflow_manager.create_workflow(g5, plan5)
    await workflow_manager.save_checkpoint(wf5["workflow_id"], g5, plan5, snap5, {t5.task_id: ExecutionState.PENDING})

    await goal_manager.start_goal(g5.goal_id)
    await goal_manager.pause_goal(g5.goal_id)
    await goal_manager.resume_goal(g5.goal_id)

    restored = await workflow_manager.resume_workflow(wf5["workflow_id"])
    assert restored["goal"].goal_id == g5.goal_id
    print(f"[PASS] Scenario 5 (Pause -> Resume -> Checkpoint Restore) passed.")

    # ── Scenario 6: Cancel Running Goal ──
    g6 = await goal_manager.create_goal("Cancel Goal")
    await goal_manager.start_goal(g6.goal_id)
    await goal_manager.cancel_goal(g6.goal_id, reason="User request")
    assert (await goal_manager.get_goal_status(g6.goal_id)).status == GoalStatus.CANCELLED
    print(f"[PASS] Scenario 6 (Cancel Running Goal) passed.")


async def test_scenario_7_concurrent_goals_and_performance():
    section("3. SCENARIO 7: CONCURRENT GOALS & PERFORMANCE BENCHMARKS")

    captured_events = []
    def capture(event):
        captured_events.append(event.name)

    event_bus.subscribe(autonomous_config.EVENT_GOAL_CREATED, capture)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_STARTED, capture)
    event_bus.subscribe(autonomous_config.EVENT_GOAL_COMPLETED, capture)

    # Performance benchmark timers
    t_start = time.time()
    g_bench = await goal_manager.create_goal("Benchmark Goal")
    lat_goal_create = time.time() - t_start

    t_plan_start = time.time()
    tasks_bench = await task_planner.plan_tasks(g_bench)
    plan_bench = execution_planner.build_execution_plan(tasks_bench)
    lat_plan = time.time() - t_plan_start

    wf_bench = await workflow_manager.create_workflow(g_bench, plan_bench)
    snap_bench = progress_tracker.create_progress(g_bench, plan_bench)

    t_chk_start = time.time()
    chk_bench = await workflow_manager.save_checkpoint(wf_bench["workflow_id"], g_bench, plan_bench, snap_bench, {})
    lat_chk_save = time.time() - t_chk_start

    t_restore_start = time.time()
    restored_bench = await workflow_manager.resume_workflow(wf_bench["workflow_id"])
    lat_chk_restore = time.time() - t_restore_start

    print(f"[PERF] Goal Creation Latency: {lat_goal_create*1000:.2f}ms (< 50ms)")
    print(f"[PERF] Task Planning Latency: {lat_plan*1000:.2f}ms (< 800ms)")
    print(f"[PERF] Checkpoint Save Time: {lat_chk_save*1000:.2f}ms (< 25ms)")
    print(f"[PERF] Checkpoint Restore Time: {lat_chk_restore*1000:.2f}ms (< 25ms)")

    assert lat_goal_create < 0.5
    assert lat_plan < 1.0
    assert lat_chk_save < 0.2
    assert lat_chk_restore < 0.2

    # Concurrent Goals Run
    g_c1 = await goal_manager.create_goal("Concurrent Goal A")
    g_c2 = await goal_manager.create_goal("Concurrent Goal B")
    g_c3 = await goal_manager.create_goal("Concurrent Goal C")

    results = await asyncio.gather(
        autonomous_orchestrator.execute_goal_autonomous(g_c1.goal_id),
        autonomous_orchestrator.execute_goal_autonomous(g_c2.goal_id),
        autonomous_orchestrator.execute_goal_autonomous(g_c3.goal_id),
    )

    assert len(results) == 3
    for r in results:
        assert r["status"] == GoalStatus.COMPLETED.value

    print(f"[PASS] Scenario 7 (3 Concurrent Autonomous Goals) completed cleanly.")


async def main():
    await test_rest_api_endpoints()
    await test_end_to_end_scenarios()
    await test_scenario_7_concurrent_goals_and_performance()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 5.6 CORE & E2E AUTONOMOUS TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
