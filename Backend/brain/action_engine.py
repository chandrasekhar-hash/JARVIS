import time
from typing import Dict, Any
from brain.models import ActionPlan, StructuredExecutionLog
from brain.conversation import reference_resolver
from brain.context import desktop_context
from brain.planner import tool_planner
from brain.executor import execution_manager
from brain.task_manager import task_manager
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log

class DesktopActionEngine:
    async def process_user_intent(
        self,
        query: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Master Pipeline:
        Intent Analysis -> Planner -> Validation -> Permission Manager -> Execution Manager / Task Manager -> Response.
        """
        t0 = time.time()
        
        # 1. Intent Analysis & Reference Resolution
        resolved_query = reference_resolver.resolve_references(query)
        context_summary = desktop_context.get_context_summary(resolved_query)
        
        log_structured(
            backend_log, 
            "INFO", 
            f"[ActionEngine] Intent Analyzed: '{resolved_query}' (Context injected: {bool(context_summary)})"
        )
        event_bus.emit("IntentAnalyzed", original_query=query, resolved_query=resolved_query)

        # 2. Action Planning
        plan: ActionPlan = tool_planner.parse_intent_to_plan(resolved_query, context_summary)
        
        # Check if plan requires LLM fallback reasoning
        if any(s.tool_name == "agent_reasoning" for s in plan.steps):
            return {
                "handled_by_engine": False,
                "resolved_query": resolved_query,
                "context_summary": context_summary,
                "plan": plan.dict()
            }

        # 3. Action Routing: Immediate vs Background Execution
        if plan.execution_mode == "background" and not dry_run:
            log_structured(backend_log, "INFO", f"[ActionEngine] Routing plan to TaskManager for background execution")
            
            async def background_exec_runner():
                return await execution_manager.execute_plan(plan, dry_run=False)
                
            task_meta = task_manager.create_task(
                background_exec_runner,
                description=f"Desktop Workflow: {resolved_query}"
            )
            
            event_bus.emit("ResponseReady", mode="background", task_id=task_meta.task_id)
            return {
                "handled_by_engine": True,
                "execution_mode": "background",
                "task_id": task_meta.task_id,
                "message": f"Desktop task launched in background (Task ID: {task_meta.task_id}). Status: {task_meta.status}",
                "plan": plan.dict()
            }

        # 4. Immediate Execution via ExecutionManager
        exec_log: StructuredExecutionLog = await execution_manager.execute_plan(plan, dry_run=dry_run)
        
        # Format response text
        if exec_log.success:
            if dry_run:
                response_text = f"Dry Run Plan Verified for '{resolved_query}':\nTools: {exec_log.selected_tools}\nPermissions: {exec_log.permissions}"
            else:
                response_text = f"Action executed successfully: {', '.join([str(r) for r in exec_log.results if r])}"
        else:
            response_text = f"Action execution encountered an issue: {exec_log.error}"

        event_bus.emit("ResponseReady", mode="immediate", success=exec_log.success)
        return {
            "handled_by_engine": True,
            "execution_mode": "immediate",
            "log": exec_log.dict(),
            "response_text": response_text
        }

desktop_action_engine = DesktopActionEngine()
