import sys
import os
import asyncio

# Add Backend root directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from brain.event_bus import event_bus
from brain.permissions import permission_manager
from tools.registry import registry
from autonomous import (
    autonomous_config,
    Goal,
    Task,
    ExecutionPlan,
    ExecutionState,
    TaskResult,
    execution_planner,
    ExecutionPlanner,
    tool_selector,
    ToolSelector,
    ToolSelectionResult,
    execution_engine,
    ExecutionEngine,
)


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_dag_generation_and_validation():
    section("1. DAG GENERATION & VALIDATION")

    t1 = Task(goal_id="g1", name="Task 1", description="Independent start task")
    t2 = Task(goal_id="g1", name="Task 2", description="Depends on T1", dependencies=[t1.task_id])
    t3 = Task(goal_id="g1", name="Task 3", description="Depends on T1", dependencies=[t1.task_id])
    t4 = Task(goal_id="g1", name="Task 4", description="Depends on T2 and T3", dependencies=[t2.task_id, t3.task_id])

    tasks = [t1, t2, t3, t4]
    plan = execution_planner.build_execution_plan(tasks)

    assert plan.goal_id == "g1"
    assert len(plan.tasks) == 4
    assert execution_planner.validate_plan(plan) is True
    print(f"[PASS] DAG built and validated successfully: {len(plan.tasks)} tasks.")

    # 2. Cycle Detection
    cycle_tasks = [
        Task(task_id="A", goal_id="g2", name="A", description="A", dependencies=["B"]),
        Task(task_id="B", goal_id="g2", name="B", description="B", dependencies=["A"]),
    ]
    cycle_plan = execution_planner.build_execution_plan(cycle_tasks)
    assert execution_planner.validate_plan(cycle_plan) is False
    print(f"[PASS] Cycle detection correctly identified circular dependency A <-> B.")


def test_topological_sort_and_batching():
    section("2. TOPOLOGICAL SORT & PARALLEL BATCHING")

    t1 = Task(task_id="T1", goal_id="g1", name="Task 1", description="Init")
    t2 = Task(task_id="T2", goal_id="g1", name="Task 2", description="Sub1", dependencies=["T1"])
    t3 = Task(task_id="T3", goal_id="g1", name="Task 3", description="Sub2", dependencies=["T1"])
    t4 = Task(task_id="T4", goal_id="g1", name="Task 4", description="Final", dependencies=["T2", "T3"])

    plan = execution_planner.build_execution_plan([t1, t2, t3, t4])

    topo_order = execution_planner.get_topological_order(plan)
    assert topo_order[0] == "T1"
    assert topo_order[-1] == "T4"
    assert topo_order.index("T1") < topo_order.index("T2")
    assert topo_order.index("T1") < topo_order.index("T3")
    print(f"[PASS] Topological sort verified: {topo_order}")

    batches = execution_planner.get_execution_batches(plan)
    assert len(batches) == 3
    assert batches[0] == ["T1"]
    assert sorted(batches[1]) == ["T2", "T3"]
    assert batches[2] == ["T4"]
    print(f"[PASS] Parallel execution batches verified: {batches}")

    # Ready task resolution
    ready_0 = execution_planner.get_ready_tasks(plan, completed_tasks=[])
    assert len(ready_0) == 1 and ready_0[0].task_id == "T1"

    ready_1 = execution_planner.get_ready_tasks(plan, completed_tasks=["T1"])
    assert len(ready_1) == 2 and set(t.task_id for t in ready_1) == {"T2", "T3"}
    print(f"[PASS] Ready tasks resolution verified.")


async def test_tool_selector():
    section("3. TOOL SELECTOR & PERMISSION VALIDATION")

    # 1. Register a test dummy tool in ToolRegistry
    @registry.register(
        name="test_dummy_tool",
        description="Dummy tool for M5.2 test suite",
        parameters={"message": {"type": "string"}},
        safety_level="safe"
    )
    def dummy_func(message: str):
        return f"Echo: {message}"

    t_valid = Task(
        goal_id="g1",
        name="Dummy Task",
        description="Run dummy tool",
        suggested_tool="test_dummy_tool",
        input_params={"message": "Hello Autonomous World"}
    )

    selection = await tool_selector.select_tool_for_task(t_valid)
    assert selection["selected_tool"] == "test_dummy_tool"
    assert selection["is_valid"] is True
    assert selection["confidence"] > 0.9
    assert selection["permission_level"] == "safe"
    print(f"[PASS] Valid tool selection: Tool='{selection['selected_tool']}' | Permission={selection['permission_level']}")

    # 2. Invalid Tool Selection (Missing required parameter)
    t_invalid_args = Task(
        goal_id="g1",
        name="Invalid Args Task",
        description="Run dummy tool without required message",
        suggested_tool="test_dummy_tool",
        input_params={}
    )
    selection_inv = await tool_selector.select_tool_for_task(t_invalid_args)
    assert selection_inv["is_valid"] is False
    assert selection_inv["confidence"] == 0.0
    print(f"[PASS] Invalid tool selection rejected correctly: Reason='{selection_inv['reason']}'")

    # 3. Permission Level Checks
    permission_manager.register_tool_permission("test_destructive_tool", "confirmation_required")
    @registry.register(
        name="test_destructive_tool",
        description="Destructive tool test",
        parameters={"confirm_delete": {"type": "boolean"}},
        safety_level="confirmation_required"
    )
    def dest_func(confirm_delete: bool):
        return "Deleted"

    t_dest = Task(
        goal_id="g1",
        name="Destructive Step",
        description="Test destructive permission check",
        suggested_tool="test_destructive_tool",
        input_params={"confirm_delete": True}
    )
    sel_dest = await tool_selector.select_tool_for_task(t_dest)
    assert sel_dest["permission_level"] in ("ask_once", "confirmation_required")
    print(f"[PASS] Permission manager level retrieved: '{sel_dest['permission_level']}'")


async def test_execution_engine_and_events():
    section("4. EXECUTION ENGINE, TIMEOUTS, CANCELLATION & EVENTS")

    captured_events = []
    def capture(event):
        captured_events.append(event.name)

    event_bus.subscribe(autonomous_config.EVENT_TASK_STARTED, capture)
    event_bus.subscribe(autonomous_config.EVENT_TASK_COMPLETED, capture)
    event_bus.subscribe(autonomous_config.EVENT_TASK_FAILED, capture)
    event_bus.subscribe(autonomous_config.EVENT_EXECUTION_STARTED, capture)
    event_bus.subscribe(autonomous_config.EVENT_EXECUTION_COMPLETED, capture)
    event_bus.subscribe(autonomous_config.EVENT_EXECUTION_CANCELLED, capture)

    # 1. Normal Task Execution
    t_exec = Task(
        goal_id="g1",
        name="Exec Task",
        description="Execute valid tool step",
        suggested_tool="test_dummy_tool",
        input_params={"message": "Execute Engine Test"}
    )
    sel = await tool_selector.select_tool_for_task(t_exec)
    res = await execution_engine.execute_task(t_exec, sel)

    assert res.status == ExecutionState.COMPLETED
    assert "Echo: Execute Engine Test" in str(res.output)
    assert res.execution_time_seconds > 0
    print(f"[PASS] Normal task execution completed: Output='{res.output}'")

    # 2. Timeout Handling Test
    @registry.register(
        name="test_slow_tool",
        description="Slow tool for timeout testing",
        parameters={},
        safety_level="safe"
    )
    async def slow_func():
        await asyncio.sleep(0.5)
        return "Slow Done"

    t_slow = Task(
        goal_id="g1",
        name="Slow Task",
        description="Tests timeout enforcement",
        suggested_tool="test_slow_tool",
        input_params={},
        timeout_seconds=0.05
    )
    sel_slow = await tool_selector.select_tool_for_task(t_slow)
    res_slow = await execution_engine.execute_task(t_slow, sel_slow)

    assert res_slow.status == ExecutionState.FAILED
    assert "timed out" in res_slow.error.lower()
    print(f"[PASS] Timeout enforcement verified: Error='{res_slow.error}'")

    # 3. Task Cancellation Test
    t_cancel = Task(
        goal_id="g1",
        name="Cancel Task",
        description="Tests pre-execution cancellation",
        suggested_tool="test_dummy_tool",
        input_params={"message": "Cancel Test"}
    )
    await execution_engine.cancel_task(t_cancel.task_id)
    sel_cancel = await tool_selector.select_tool_for_task(t_cancel)
    res_cancel = await execution_engine.execute_task(t_cancel, sel_cancel)

    assert res_cancel.status == ExecutionState.CANCELLED
    print(f"[PASS] Task cancellation verified: Status={res_cancel.status.value}")

    # 4. EventBus Emissions Verification
    print(f"[PASS] EventBus emissions captured: {captured_events}")
    assert autonomous_config.EVENT_TASK_STARTED in captured_events
    assert autonomous_config.EVENT_TASK_COMPLETED in captured_events
    assert autonomous_config.EVENT_TASK_FAILED in captured_events
    assert autonomous_config.EVENT_EXECUTION_STARTED in captured_events
    assert autonomous_config.EVENT_EXECUTION_COMPLETED in captured_events
    assert autonomous_config.EVENT_EXECUTION_CANCELLED in captured_events


async def main():
    test_dag_generation_and_validation()
    test_topological_sort_and_batching()
    await test_tool_selector()
    await test_execution_engine_and_events()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 5.2 CORE AUTONOMOUS TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
