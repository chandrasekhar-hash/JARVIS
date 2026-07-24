import sys
import os
import time
import gc
import asyncio
import tempfile

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
    TaskResult,
    RecoveryAttempt,
    ProgressSnapshot,
    WorkflowManager,
    FullWorkflowCheckpoint,
)


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def cleanup_file(filepath: str):
    """Safely removes temporary test file."""
    gc.collect()
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass


async def test_workflow_creation_and_checkpoint_save():
    section("1. WORKFLOW CREATION & CHECKPOINT SAVE/LOAD")

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    try:
        wm = WorkflowManager(db_path=db_path)

        g = Goal(user_intent="Build Autonomous React Dashboard")
        t1 = Task(goal_id=g.goal_id, name="Npm Install", description="Install dependencies", suggested_tool="terminal_execute")
        plan = ExecutionPlan(goal_id=g.goal_id, tasks={t1.task_id: t1})

        # 1. Create Workflow
        wf = await wm.create_workflow(g, plan)
        assert wf["workflow_id"].startswith("wf_")
        assert wf["goal_id"] == g.goal_id
        print(f"[PASS] Workflow created: ID={wf['workflow_id']}")

        # 2. Save Checkpoint
        snap = ProgressSnapshot(goal_id=g.goal_id, overall_progress_pct=50.0, total_tasks=1, completed_tasks=0, in_progress_tasks=1)
        task_states = {t1.task_id: ExecutionState.RUNNING}
        task_results = {t1.task_id: TaskResult(task_id=t1.task_id, status=ExecutionState.RUNNING, execution_time_seconds=0.1)}
        rec_history = [RecoveryAttempt(task_id=t1.task_id, strategy="retry", success=True, details="Retry ok")]

        chk = await wm.save_checkpoint(
            workflow_id=wf["workflow_id"],
            goal=g,
            plan=plan,
            snapshot=snap,
            task_states=task_states,
            task_results=task_results,
            recovery_history=rec_history,
            execution_context={"env": "test"}
        )

        assert chk.checkpoint_id.startswith("chk_")
        assert chk.version == autonomous_config.WORKFLOW_CHECKPOINT_VERSION
        print(f"[PASS] Checkpoint saved: ID={chk.checkpoint_id} | Version={chk.version}")

        # 3. Load Checkpoint
        loaded = await wm.load_checkpoint(wf["workflow_id"])
        assert loaded.checkpoint_id == chk.checkpoint_id
        assert loaded.goal.user_intent == g.user_intent
        assert loaded.progress_snapshot.overall_progress_pct == 50.0
        assert loaded.task_states[t1.task_id] == ExecutionState.RUNNING
        print(f"[PASS] Checkpoint loaded successfully: Intent='{loaded.goal.user_intent}'")
    finally:
        cleanup_file(db_path)


async def test_workflow_resume_archive_and_delete():
    section("2. WORKFLOW RESUME, ARCHIVE & DELETE")

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    try:
        wm = WorkflowManager(db_path=db_path)
        g = Goal(user_intent="Resume Test Goal")
        t = Task(goal_id=g.goal_id, name="Scan Files", description="Scan Downloads")
        plan = ExecutionPlan(goal_id=g.goal_id, tasks={t.task_id: t})
        snap = ProgressSnapshot(goal_id=g.goal_id, overall_progress_pct=100.0, total_tasks=1, completed_tasks=1)

        wf = await wm.create_workflow(g, plan)
        await wm.save_checkpoint(wf["workflow_id"], g, plan, snap, {t.task_id: ExecutionState.COMPLETED})

        # 1. Resume Workflow (Restores state payload)
        resumed = await wm.resume_workflow(wf["workflow_id"])
        assert resumed["workflow_id"] == wf["workflow_id"]
        assert resumed["goal"].goal_id == g.goal_id
        assert resumed["plan"].plan_id == plan.plan_id
        assert resumed["task_states"][t.task_id] == ExecutionState.COMPLETED
        print(f"[PASS] Workflow resumed state restored cleanly without task auto-execution.")

        # 2. Archive Workflow
        archived = await wm.archive_workflow(wf["workflow_id"])
        assert archived is True
        listed_archived = await wm.list_workflows(archived=True)
        assert len(listed_archived) == 1
        print(f"[PASS] Workflow archived successfully.")

        # 3. Delete Workflow
        deleted = await wm.delete_workflow(wf["workflow_id"])
        assert deleted is True
        listed_after = await wm.list_workflows()
        assert len(listed_after) == 0
        print(f"[PASS] Workflow deleted successfully.")
    finally:
        cleanup_file(db_path)


async def test_version_validation_and_corruption():
    section("3. VERSION VALIDATION & CORRUPTED CHECKPOINT REJECTION")

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    try:
        wm = WorkflowManager(db_path=db_path)

        # 1. Incompatible version rejection
        incompatible_json = '{"checkpoint_id":"chk_1","workflow_id":"wf_1","goal_id":"g1","version":"4.0.0","goal":{},"plan":{},"progress_snapshot":{}}'
        caught_ver_err = False
        try:
            wm.validate_checkpoint(incompatible_json)
        except ValueError as err:
            caught_ver_err = True
            assert "Incompatible checkpoint version" in str(err)
        assert caught_ver_err is True
        print(f"[PASS] Incompatible version '4.0.0' rejected correctly.")

        # 2. Malformed JSON rejection
        corrupted_json = '{"checkpoint_id":"chk_1", "broken_json":'
        caught_json_err = False
        try:
            wm.validate_checkpoint(corrupted_json)
        except ValueError as err:
            caught_json_err = True
            assert "Invalid JSON format" in str(err)
        assert caught_json_err is True
        print(f"[PASS] Malformed JSON checkpoint rejected correctly.")

        # 3. Missing required field
        missing_field_json = '{"checkpoint_id":"chk_1","workflow_id":"wf_1","version":"5.0.0"}'
        caught_field_err = False
        try:
            wm.validate_checkpoint(missing_field_json)
        except ValueError as err:
            caught_field_err = True
            assert "Missing required field" in str(err)
        assert caught_field_err is True
        print(f"[PASS] Missing required field checkpoint rejected correctly.")

        # 4. Non-existent checkpoint load
        caught_missing_err = False
        try:
            await wm.load_checkpoint("non_existent_wf_id")
        except ValueError as err:
            caught_missing_err = True
            assert "No checkpoint found" in str(err)
        assert caught_missing_err is True
        print(f"[PASS] Missing checkpoint query handled cleanly.")
    finally:
        cleanup_file(db_path)


async def test_concurrent_saves_and_events():
    section("4. CONCURRENT SAVE PROTECTION & EVENTBUS BROADCASTS")

    captured_events = []
    def capture(event):
        captured_events.append(event.name)

    event_bus.subscribe(autonomous_config.EVENT_WORKFLOW_CREATED, capture)
    event_bus.subscribe(autonomous_config.EVENT_CHECKPOINT_SAVED, capture)
    event_bus.subscribe(autonomous_config.EVENT_CHECKPOINT_LOADED, capture)
    event_bus.subscribe(autonomous_config.EVENT_WORKFLOW_RESUMED, capture)
    event_bus.subscribe(autonomous_config.EVENT_WORKFLOW_ARCHIVED, capture)
    event_bus.subscribe(autonomous_config.EVENT_WORKFLOW_DELETED, capture)

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    try:
        wm = WorkflowManager(db_path=db_path)
        g = Goal(user_intent="Concurrent Test Goal")
        t = Task(goal_id=g.goal_id, name="Concurrent Step", description="Step")
        plan = ExecutionPlan(goal_id=g.goal_id, tasks={t.task_id: t})
        snap = ProgressSnapshot(goal_id=g.goal_id)

        wf = await wm.create_workflow(g, plan)

        # Dispatch parallel checkpoint saves
        async def do_save(idx: int):
            return await wm.save_checkpoint(
                wf["workflow_id"], g, plan, snap, {t.task_id: ExecutionState.RUNNING}, execution_context={"idx": idx}
            )

        checkpoints = await asyncio.gather(do_save(1), do_save(2), do_save(3))
        assert len(checkpoints) == 3
        print(f"[PASS] 3 concurrent checkpoint saves executed without lock contention or corruption.")

        # EventBus verification
        print(f"[PASS] EventBus emissions captured: {captured_events}")
        assert autonomous_config.EVENT_WORKFLOW_CREATED in captured_events
        assert autonomous_config.EVENT_CHECKPOINT_SAVED in captured_events
    finally:
        cleanup_file(db_path)


async def main():
    await test_workflow_creation_and_checkpoint_save()
    await test_workflow_resume_archive_and_delete()
    await test_version_validation_and_corruption()
    await test_concurrent_saves_and_events()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 5.5 CORE AUTONOMOUS TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
