import time
from typing import List, Dict, Any, Optional
from brain.models import ActionPlan, ActionStep, StructuredExecutionLog
from brain.permissions import permission_manager
from brain.context import desktop_context
from brain.conversation import reference_resolver
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log

class ExecutionManager:
    async def execute_plan(
        self,
        plan: ActionPlan,
        dry_run: bool = False
    ) -> StructuredExecutionLog:
        """
        Executes an ActionPlan through the pipeline:
        Planner -> Validation -> Permission Manager -> Execution Manager -> Response.
        Supports dry_run=True mode.
        """
        from tools.registry import registry
        t0 = time.time()
        selected_tools = [step.tool_name for step in plan.steps]
        permissions = [permission_manager.get_permission_level(tool) for tool in selected_tools]
        plan_summary = [step.dict() for step in plan.steps]

        log_structured(backend_log, "INFO", f"[Executor] Starting execution for intent '{plan.intent}' (dry_run={dry_run})")
        event_bus.emit("ActionPlanned", intent=plan.intent, tools=selected_tools, dry_run=dry_run)

        # 1. Validation phase
        registered_tool_names = [t["function"]["name"] for t in registry.get_tool_schemas()]
        for step in plan.steps:
            if step.tool_name != "agent_reasoning" and step.tool_name not in registered_tool_names:
                err_msg = f"Validation failed: Tool '{step.tool_name}' is not registered."
                log_structured(backend_log, "ERROR", f"[Executor] {err_msg}")
                return StructuredExecutionLog(
                    intent=plan.intent,
                    generated_plan=plan_summary,
                    selected_tools=selected_tools,
                    permissions=permissions,
                    execution_time_seconds=round(time.time() - t0, 3),
                    dry_run=dry_run,
                    success=False,
                    results=[],
                    error=err_msg
                )

        event_bus.emit("ValidationPassed", intent=plan.intent)

        # 2. Permission check phase
        for step in plan.steps:
            perm_status = permission_manager.verify_permission(step.tool_name, step.arguments)
            if perm_status == "denied":
                err_msg = f"Permission denied for tool '{step.tool_name}'."
                log_structured(backend_log, "WARNING", f"[Executor] {err_msg}")
                return StructuredExecutionLog(
                    intent=plan.intent,
                    generated_plan=plan_summary,
                    selected_tools=selected_tools,
                    permissions=permissions,
                    execution_time_seconds=round(time.time() - t0, 3),
                    dry_run=dry_run,
                    success=False,
                    results=[],
                    error=err_msg
                )

        event_bus.emit("PermissionGranted", intent=plan.intent)

        # 3. Dry Run Mode
        if dry_run:
            log_structured(backend_log, "INFO", f"[Executor] Dry run mode completed for '{plan.intent}'")
            return StructuredExecutionLog(
                intent=plan.intent,
                generated_plan=plan_summary,
                selected_tools=selected_tools,
                permissions=permissions,
                execution_time_seconds=round(time.time() - t0, 3),
                dry_run=True,
                success=True,
                results=["Dry run plan verified successfully. No tools executed."]
            )

        # 4. Actual Tool Execution & Recovery Handling
        results = []
        for step in plan.steps:
            if step.tool_name == "agent_reasoning":
                continue

            try:
                log_structured(backend_log, "INFO", f"[Executor] Executing tool '{step.tool_name}' with args {step.arguments}")
                res = await registry.execute(step.tool_name, **step.arguments)
                results.append(res)

                # Update Desktop Context & Conversation Memory
                desktop_context.update_from_tool_execution(step.tool_name, step.arguments, res)
                if "app" in step.tool_name:
                    name = step.arguments.get("name") or step.arguments.get("app_name")
                    if name:
                        reference_resolver.register_mention("app", str(name))
                elif "browser" in step.tool_name:
                    url = step.arguments.get("urls") or step.arguments.get("query")
                    if url:
                        reference_resolver.register_mention("url", str(url))

            except Exception as e:
                # Recovery handling: attempt retry
                log_structured(backend_log, "WARNING", f"[Executor] Tool '{step.tool_name}' failed: {str(e)}. Attempting recovery...")
                try:
                    res_retry = await registry.execute(step.tool_name, **step.arguments)
                    results.append(res_retry)
                    log_structured(backend_log, "INFO", f"[Executor] Recovery retry succeeded for '{step.tool_name}'")
                except Exception as e_retry:
                    err_final = f"Step {step.step_id} ({step.tool_name}) failed: {str(e_retry)}"
                    log_structured(backend_log, "ERROR", f"[Executor] Recovery failed: {err_final}")
                    return StructuredExecutionLog(
                        intent=plan.intent,
                        generated_plan=plan_summary,
                        selected_tools=selected_tools,
                        permissions=permissions,
                        execution_time_seconds=round(time.time() - t0, 3),
                        dry_run=False,
                        success=False,
                        results=results,
                        error=err_final
                    )

        log_ok = StructuredExecutionLog(
            intent=plan.intent,
            generated_plan=plan_summary,
            selected_tools=selected_tools,
            permissions=permissions,
            execution_time_seconds=round(time.time() - t0, 3),
            dry_run=False,
            success=True,
            results=results
        )
        event_bus.emit("TaskCompleted", intent=plan.intent, success=True)
        return log_ok

execution_manager = ExecutionManager()
