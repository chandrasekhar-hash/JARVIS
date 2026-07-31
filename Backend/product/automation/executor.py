"""
JARVIS Product 1.7 - Action Executor.
Executes workflow action steps strictly through Product 1.5 Tool Execution Engine (ProductToolExecutionManager).
"""

import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from .interfaces import IActionExecutor
from .models import Workflow, ActionStep, WorkflowRunRecord, RunStatus, ExecutionStrategy
from .recovery import RetryManager, TimeoutManager
from ..tools import tool_execution_manager_instance, ExecutionContext

logger = logging.getLogger(__name__)


class ActionExecutor(IActionExecutor):
    def execute_step(
        self,
        step: ActionStep,
        owner_id: str,
        correlation_id: str,
    ) -> Dict[str, Any]:
        """
        Delegates tool execution strictly to Product 1.5 Tool Execution Engine.
        """
        context = ExecutionContext(
            correlation_id=correlation_id,
            tool_id=step.tool_id,
            user_id=owner_id,
        )

        def action_wrapper() -> Dict[str, Any]:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        res = pool.submit(
                            asyncio.run,
                            tool_execution_manager_instance.execute_tool(
                                tool_id=step.tool_id,
                                kwargs=step.arguments,
                                user_id=owner_id,
                                correlation_id=correlation_id,
                            )
                        ).result()
                else:
                    res = loop.run_until_complete(
                        tool_execution_manager_instance.execute_tool(
                            tool_id=step.tool_id,
                            kwargs=step.arguments,
                            user_id=owner_id,
                            correlation_id=correlation_id,
                        )
                    )
            except Exception:
                res = asyncio.run(
                    tool_execution_manager_instance.execute_tool(
                        tool_id=step.tool_id,
                        kwargs=step.arguments,
                        user_id=owner_id,
                        correlation_id=correlation_id,
                    )
                )

            return {
                "success": res.success,
                "status": res.status.value,
                "result_payload": res.result_payload,
                "error_message": res.error_message,
                "duration_ms": res.duration_ms,
            }

        # Apply timeout & retry wrapper
        return TimeoutManager.execute_with_timeout(
            action_func=action_wrapper,
            timeout_seconds=step.timeout_seconds,
        )

    def execute_workflow_actions(
        self,
        workflow: Workflow,
        run_record: WorkflowRunRecord,
    ) -> bool:
        start_time = time.time()
        run_record.status = RunStatus.RUNNING
        step_logs: List[Dict[str, Any]] = []

        overall_success = True

        for idx, step in enumerate(workflow.actions):
            step_start = time.time()

            # Execute step via P1.5 retry/recovery wrapper
            step_result = RetryManager.execute_with_retry(
                action_func=lambda: self.execute_step(step, workflow.owner, run_record.run_id),
                retry_policy=workflow.retry_policy,
            )

            step_duration = (time.time() - step_start) * 1000.0
            is_step_success = step_result.get("success", False) or step_result.get("status") == "SUCCESS"

            step_log = {
                "step_id": step.step_id,
                "tool_id": step.tool_id,
                "success": is_step_success,
                "duration_ms": step_duration,
                "result": step_result,
            }
            step_logs.append(step_log)

            if is_step_success:
                run_record.steps_completed += 1
            else:
                overall_success = False
                run_record.error_details = step_result.get("error_message", f"Step {step.step_id} failed.")
                if not step.continue_on_failure:
                    logger.warning(f"Workflow {workflow.workflow_id} halted at step {step.step_id} due to failure.")
                    break

        run_record.end_time = datetime.utcnow() if 'datetime' in globals() else None
        run_record.duration_ms = (time.time() - start_time) * 1000.0
        run_record.step_logs_json = json.dumps(step_logs)
        run_record.status = RunStatus.COMPLETED if overall_success else RunStatus.FAILED

        return overall_success
