import time
import asyncio
from typing import Dict, List, Optional, Any
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log
from autonomous.models import (
    Goal, Task, ExecutionPlan, TaskResult, GoalStatus, ExecutionState, ProgressSnapshot, RecoveryAttempt
)
from autonomous.config import autonomous_config
from autonomous.goal_manager import goal_manager
from autonomous.task_planner import task_planner
from autonomous.execution_planner import execution_planner
from autonomous.tool_selector import tool_selector
from autonomous.execution_engine import execution_engine
from autonomous.progress_tracker import progress_tracker
from autonomous.recovery_engine import recovery_engine, RecoveryStrategy
from autonomous.workflow_manager import workflow_manager, FullWorkflowCheckpoint


class AutonomousOrchestrator:
    """Orchestrates end-to-end autonomous goal execution, monitoring, checkpointing, and failure recovery."""

    async def execute_goal_autonomous(self, goal_id: str) -> Dict[str, Any]:
        """Runs complete autonomous execution loop for a registered Goal."""
        goal = await goal_manager.get_goal_status(goal_id)
        if not goal:
            raise ValueError(f"Goal '{goal_id}' not found.")

        # 1. Plan Tasks & Build DAG Plan
        tasks = await task_planner.plan_tasks(goal)
        plan = execution_planner.build_execution_plan(tasks)

        # 2. Create Workflow & Init Progress Tracking
        wf = await workflow_manager.create_workflow(goal, plan)
        workflow_id = wf["workflow_id"]
        snapshot = progress_tracker.create_progress(goal, plan)

        # Start Goal
        await goal_manager.start_goal(goal_id)

        completed_tasks: Set[str] = set()
        task_states: Dict[str, ExecutionState] = {t_id: ExecutionState.PENDING for t_id in plan.tasks}
        task_results: Dict[str, TaskResult] = {}
        recovery_history: List[RecoveryAttempt] = []

        log_structured(backend_log, "INFO", f"[Orchestrator] Starting autonomous loop for Goal {goal_id} (Workflow {workflow_id}).")

        # Initial Checkpoint
        await workflow_manager.save_checkpoint(
            workflow_id=workflow_id,
            goal=goal,
            plan=plan,
            snapshot=snapshot,
            task_states=task_states,
            task_results=task_results,
            recovery_history=recovery_history
        )

        # 3. Execution Loop
        while len(completed_tasks) < len(plan.tasks):
            # Check if goal was cancelled or paused externally
            curr_goal = await goal_manager.get_goal_status(goal_id)
            if curr_goal and curr_goal.status in (GoalStatus.CANCELLED, GoalStatus.PAUSED):
                log_structured(backend_log, "INFO", f"[Orchestrator] Goal {goal_id} loop interrupted (Status: {curr_goal.status.value}).")
                snapshot = progress_tracker.get_snapshot(goal_id)
                await workflow_manager.save_checkpoint(workflow_id, curr_goal, plan, snapshot, task_states, task_results, recovery_history)
                return {
                    "goal_id": goal_id,
                    "workflow_id": workflow_id,
                    "status": curr_goal.status.value,
                    "progress_snapshot": snapshot
                }

            ready_tasks = execution_planner.get_ready_tasks(plan, list(completed_tasks))
            if not ready_tasks:
                if len(completed_tasks) < len(plan.tasks):
                    # Potential failure or unhandled deadlock
                    log_structured(backend_log, "WARNING", f"[Orchestrator] No ready tasks available for Goal {goal_id}.")
                    break

            for task in ready_tasks:
                if task.task_id in completed_tasks:
                    continue

                # Select Tool
                sel_tool = await tool_selector.select_tool_for_task(task)

                # Progress & State -> RUNNING
                progress_tracker.update_goal_task_progress(goal_id, task.task_id, ExecutionState.RUNNING)
                task_states[task.task_id] = ExecutionState.RUNNING

                # Execute Task
                result = await execution_engine.execute_task(task, sel_tool)
                task_results[task.task_id] = result

                if result.status == ExecutionState.COMPLETED:
                    completed_tasks.add(task.task_id)
                    task_states[task.task_id] = ExecutionState.COMPLETED
                    execution_planner.mark_task_complete(plan, task.task_id)
                    snapshot = progress_tracker.update_goal_task_progress(goal_id, task.task_id, ExecutionState.COMPLETED)
                    await workflow_manager.save_checkpoint(workflow_id, goal, plan, snapshot, task_states, task_results, recovery_history)

                else:
                    # Task Failed -> Evaluate Recovery
                    progress_tracker.update_goal_task_progress(goal_id, task.task_id, ExecutionState.FAILED)
                    task_states[task.task_id] = ExecutionState.FAILED

                    decision = await recovery_engine.evaluate_and_recover(task, result, plan, goal)
                    rec_att = RecoveryAttempt(
                        task_id=task.task_id,
                        strategy=decision.strategy.value,
                        success=(decision.strategy != RecoveryStrategy.ABORT_GOAL),
                        details=decision.reason
                    )
                    recovery_history.append(rec_att)

                    if decision.strategy == RecoveryStrategy.RETRY:
                        if decision.backoff_delay_seconds > 0:
                            await asyncio.sleep(min(decision.backoff_delay_seconds, 0.1))
                        # Retry step
                        retry_res = await execution_engine.execute_task(task, sel_tool)
                        task_results[task.task_id] = retry_res
                        if retry_res.status == ExecutionState.COMPLETED:
                            completed_tasks.add(task.task_id)
                            task_states[task.task_id] = ExecutionState.COMPLETED
                            execution_planner.mark_task_complete(plan, task.task_id)
                            recovery_engine.reset_task_recovery_state(task.task_id)
                            snapshot = progress_tracker.update_goal_task_progress(goal_id, task.task_id, ExecutionState.COMPLETED)
                            await workflow_manager.save_checkpoint(workflow_id, goal, plan, snapshot, task_states, task_results, recovery_history)

                    elif decision.strategy == RecoveryStrategy.ALTERNATIVE_TOOL and decision.alternative_tool:
                        alt_task = task.model_copy()
                        alt_task.suggested_tool = decision.alternative_tool
                        alt_sel = await tool_selector.select_tool_for_task(alt_task)
                        alt_res = await execution_engine.execute_task(alt_task, alt_sel)
                        task_results[task.task_id] = alt_res
                        if alt_res.status == ExecutionState.COMPLETED:
                            completed_tasks.add(task.task_id)
                            task_states[task.task_id] = ExecutionState.COMPLETED
                            execution_planner.mark_task_complete(plan, task.task_id)
                            snapshot = progress_tracker.update_goal_task_progress(goal_id, task.task_id, ExecutionState.COMPLETED)
                            await workflow_manager.save_checkpoint(workflow_id, goal, plan, snapshot, task_states, task_results, recovery_history)

                    elif decision.strategy == RecoveryStrategy.DYNAMIC_REPLAN and decision.replacement_tasks:
                        for new_t in decision.replacement_tasks:
                            plan.tasks[new_t.task_id] = new_t
                            plan.dag_edges[new_t.task_id] = list(new_t.dependencies)
                            task_states[new_t.task_id] = ExecutionState.PENDING

                        # Mark original failed task as skipped/handled
                        completed_tasks.add(task.task_id)
                        task_states[task.task_id] = ExecutionState.SKIPPED
                        snapshot = progress_tracker.get_snapshot(goal_id)
                        await workflow_manager.save_checkpoint(workflow_id, goal, plan, snapshot, task_states, task_results, recovery_history)

                    else:
                        # User Escalation or Abort Goal
                        await goal_manager.fail_goal(goal_id, decision.reason)
                        progress_tracker.fail_goal(goal_id, decision.reason)
                        snapshot = progress_tracker.get_snapshot(goal_id)
                        await workflow_manager.save_checkpoint(workflow_id, goal, plan, snapshot, task_states, task_results, recovery_history)
                        return {
                            "goal_id": goal_id,
                            "workflow_id": workflow_id,
                            "status": GoalStatus.FAILED.value,
                            "reason": decision.reason,
                            "progress_snapshot": snapshot
                        }

        # 4. Final Completion
        await goal_manager.complete_goal(goal_id, "Autonomous execution finished successfully.")
        snapshot = progress_tracker.complete_goal(goal_id)
        await workflow_manager.save_checkpoint(workflow_id, goal, plan, snapshot, task_states, task_results, recovery_history)
        await workflow_manager.archive_workflow(workflow_id)

        log_structured(backend_log, "INFO", f"[Orchestrator] Goal {goal_id} completed successfully.")

        return {
            "goal_id": goal_id,
            "workflow_id": workflow_id,
            "status": GoalStatus.COMPLETED.value,
            "progress_snapshot": snapshot
        }


autonomous_orchestrator = AutonomousOrchestrator()
