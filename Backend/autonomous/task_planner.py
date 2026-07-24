import re
import json
import uuid
from typing import List, Dict, Any, Optional
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log
from autonomous.models import Goal, Task
from autonomous.interfaces import ITaskPlanner
from autonomous.config import autonomous_config


class TaskPlanner(ITaskPlanner):
    """Subsystem responsible for breaking high-level goals into DAG task nodes."""

    async def plan_tasks(self, goal: Goal, context: Optional[Dict[str, Any]] = None) -> List[Task]:
        """Decomposes a user goal into a list of structured Task objects."""
        log_structured(
            backend_log, 
            "INFO", 
            f"[TaskPlanner] Planning tasks for Goal: '{goal.user_intent}' (ID: {goal.goal_id})"
        )

        tasks: List[Task] = []
        intent_lower = goal.user_intent.lower().strip()

        # 1. Intent Pattern Matching for Heuristic Plan Generation
        if "organize" in intent_lower and ("downloads" in intent_lower or "folder" in intent_lower):
            t1 = Task(
                goal_id=goal.goal_id,
                name="Scan Folder",
                description="List and categorize files in the target directory",
                suggested_tool="fs_list_directory",
                input_params={"path": goal.metadata.get("path", "Downloads")},
                dependencies=[]
            )
            t2 = Task(
                goal_id=goal.goal_id,
                name="Categorize & Move Files",
                description="Move files into categorized subfolders (Documents, Images, Archives)",
                suggested_tool="fs_organize_files",
                input_params={"target_folder": goal.metadata.get("path", "Downloads")},
                dependencies=[t1.task_id]
            )
            t3 = Task(
                goal_id=goal.goal_id,
                name="Verify Organization",
                description="Perform post-organization check and generate summary report",
                suggested_tool="fs_verify_structure",
                input_params={"target_folder": goal.metadata.get("path", "Downloads")},
                dependencies=[t2.task_id]
            )
            tasks = [t1, t2, t3]

        elif "summarize" in intent_lower or "email" in intent_lower:
            t1 = Task(
                goal_id=goal.goal_id,
                name="Fetch Inbox Context",
                description="Retrieve active or recent email/message threads",
                suggested_tool="browser_read_page",
                input_params={"target": "inbox"},
                dependencies=[]
            )
            t2 = Task(
                goal_id=goal.goal_id,
                name="Generate Summaries",
                description="Synthesize key bullet points and action items",
                suggested_tool="ai_summarize",
                input_params={"focus": "action_items"},
                dependencies=[t1.task_id]
            )
            tasks = [t1, t2]

        elif "build" in intent_lower or "project" in intent_lower:
            t1 = Task(
                goal_id=goal.goal_id,
                name="Inspect Project Directory",
                description="Check package.json or setup files in project path",
                suggested_tool="fs_list_directory",
                input_params={"path": goal.metadata.get("path", ".")},
                dependencies=[]
            )
            t2 = Task(
                goal_id=goal.goal_id,
                name="Install Dependencies",
                description="Execute dependency installation script (npm install / pip install)",
                suggested_tool="terminal_execute",
                input_params={"command": "npm install"},
                dependencies=[t1.task_id]
            )
            t3 = Task(
                goal_id=goal.goal_id,
                name="Run Build Script",
                description="Execute build command (npm run build)",
                suggested_tool="terminal_execute",
                input_params={"command": "npm run build"},
                dependencies=[t2.task_id]
            )
            tasks = [t1, t2, t3]

        else:
            # 2. General Multi-Step Clause Splitting
            sub_clauses = [s.strip() for s in re.split(r'\b(?:and then|and|then)\b|;', goal.user_intent, flags=re.IGNORECASE) if s.strip()]
            prev_task_id: Optional[str] = None

            for idx, clause in enumerate(sub_clauses, 1):
                t = Task(
                    goal_id=goal.goal_id,
                    name=f"Step {idx}: {clause[:30]}",
                    description=clause,
                    suggested_tool="agent_reasoning",
                    input_params={"query": clause},
                    dependencies=[prev_task_id] if prev_task_id else []
                )
                tasks.append(t)
                prev_task_id = t.task_id

        # Emit TaskCreated events for each task
        for t in tasks:
            event_bus.emit(
                autonomous_config.EVENT_TASK_CREATED,
                task_id=t.task_id,
                goal_id=t.goal_id,
                name=t.name,
                dependencies=t.dependencies
            )

        log_structured(
            backend_log, 
            "INFO", 
            f"[TaskPlanner] Created {len(tasks)} tasks for goal: {goal.goal_id}"
        )
        return tasks

    async def replan_subgraph(self, goal: Goal, failed_task: Task, error_context: str) -> List[Task]:
        """Regenerates replacement subgraph tasks for a failed execution step."""
        log_structured(
            backend_log, 
            "WARNING", 
            f"[TaskPlanner] Replanning subgraph for failed task '{failed_task.name}' (Error: {error_context})"
        )

        recovery_task = Task(
            goal_id=goal.goal_id,
            name=f"Recover: {failed_task.name}",
            description=f"Alternative execution for '{failed_task.name}' following error: {error_context}",
            suggested_tool="agent_reasoning",
            input_params={"query": f"Alternative step for failed task {failed_task.name}", "error": error_context},
            dependencies=failed_task.dependencies,
            max_retries=1
        )

        event_bus.emit(
            autonomous_config.EVENT_TASK_CREATED,
            task_id=recovery_task.task_id,
            goal_id=recovery_task.goal_id,
            name=recovery_task.name,
            dependencies=recovery_task.dependencies
        )

        return [recovery_task]


task_planner = TaskPlanner()
