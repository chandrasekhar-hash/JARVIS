from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from autonomous import (
    goal_manager,
    task_planner,
    execution_planner,
    progress_tracker,
    workflow_manager,
    GoalStatus,
    ExecutionState,
)
from autonomous.orchestrator import autonomous_orchestrator

router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])


class GoalCreateRequest(BaseModel):
    user_intent: str = Field(..., description="Natural language intent for autonomous goal")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional priority or target parameters")


class GoalCancelRequest(BaseModel):
    reason: Optional[str] = Field(default="", description="Reason for goal cancellation")


# ==================================================
# GOAL REST API ENDPOINTS
# ==================================================

@router.post("/goals", status_code=status.HTTP_201_CREATED)
async def create_goal_endpoint(req: GoalCreateRequest):
    """Creates a new high-level autonomous goal and generates initial task plan."""
    if not req.user_intent or not req.user_intent.strip():
        raise HTTPException(status_code=400, detail="user_intent cannot be empty.")

    try:
        goal = await goal_manager.create_goal(req.user_intent.strip(), req.metadata)
        tasks = await task_planner.plan_tasks(goal)
        plan = execution_planner.build_execution_plan(tasks)
        snapshot = progress_tracker.create_progress(goal, plan)

        return {
            "status": "success",
            "goal": goal.model_dump(),
            "plan": plan.model_dump(),
            "progress_snapshot": snapshot.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create goal: {str(e)}")


@router.get("/goals")
async def list_goals_endpoint(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100)
):
    """Lists registered autonomous goals filtered by status."""
    try:
        goals = await goal_manager.list_goals(status=status_filter, limit=limit)
        return {"count": len(goals), "goals": [g.model_dump() for g in goals]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list goals: {str(e)}")


@router.get("/goals/{goal_id}")
async def get_goal_endpoint(goal_id: str):
    """Retrieves detailed status and progress snapshot for a specific goal."""
    goal = await goal_manager.get_goal_status(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal '{goal_id}' not found.")

    try:
        snapshot = progress_tracker.get_snapshot(goal_id)
        return {
            "goal": goal.model_dump(),
            "progress_snapshot": snapshot.model_dump()
        }
    except ValueError:
        return {
            "goal": goal.model_dump(),
            "progress_snapshot": None
        }


@router.post("/goals/{goal_id}/start")
async def start_goal_endpoint(goal_id: str):
    """Initiates autonomous execution loop for a registered goal."""
    goal = await goal_manager.get_goal_status(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal '{goal_id}' not found.")

    if goal.status not in (GoalStatus.CREATED, GoalStatus.PLANNING, GoalStatus.PAUSED):
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot start goal in state '{goal.status.value}'. Must be CREATED, PLANNING, or PAUSED."
        )

    try:
        # Dispatch autonomous loop as async background task or return status
        res = await autonomous_orchestrator.execute_goal_autonomous(goal_id)
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Goal autonomous execution failed: {str(e)}")


@router.post("/goals/{goal_id}/pause")
async def pause_goal_endpoint(goal_id: str):
    """Pauses an active autonomous goal."""
    goal = await goal_manager.get_goal_status(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal '{goal_id}' not found.")

    try:
        paused = await goal_manager.pause_goal(goal_id)
        if not paused:
            raise HTTPException(status_code=400, detail=f"Cannot pause goal in status '{goal.status.value}'.")

        snapshot = progress_tracker.pause_goal(goal_id)
        return {"status": "success", "goal_status": "paused", "progress_snapshot": snapshot.model_dump()}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.post("/goals/{goal_id}/resume")
async def resume_goal_endpoint(goal_id: str):
    """Resumes execution of a paused autonomous goal."""
    goal = await goal_manager.get_goal_status(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal '{goal_id}' not found.")

    try:
        resumed = await goal_manager.resume_goal(goal_id)
        if not resumed:
            raise HTTPException(status_code=400, detail=f"Cannot resume goal in status '{goal.status.value}'.")

        snapshot = progress_tracker.resume_goal(goal_id)
        return {"status": "success", "goal_status": "in_progress", "progress_snapshot": snapshot.model_dump()}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.post("/goals/{goal_id}/cancel")
async def cancel_goal_endpoint(goal_id: str, req: Optional[GoalCancelRequest] = None):
    """Cancels an active or pending autonomous goal."""
    goal = await goal_manager.get_goal_status(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal '{goal_id}' not found.")

    reason = req.reason if req else ""
    try:
        cancelled = await goal_manager.cancel_goal(goal_id, reason=reason)
        if not cancelled:
            raise HTTPException(status_code=400, detail=f"Cannot cancel goal in status '{goal.status.value}'.")

        snapshot = progress_tracker.cancel_goal(goal_id, reason=reason)
        return {"status": "success", "goal_status": "cancelled", "progress_snapshot": snapshot.model_dump()}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.get("/goals/{goal_id}/progress")
async def get_goal_progress_endpoint(goal_id: str):
    """Returns live progress snapshot for a goal."""
    try:
        snapshot = progress_tracker.get_snapshot(goal_id)
        return snapshot.model_dump()
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Goal progress snapshot for '{goal_id}' not found.")


# ==================================================
# WORKFLOW & CHECKPOINT REST API ENDPOINTS
# ==================================================

@router.get("/workflows")
async def list_workflows_endpoint(
    archived: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Lists registered workflows from persistence layer."""
    try:
        workflows = await workflow_manager.list_workflows(archived=archived, limit=limit)
        return {"count": len(workflows), "workflows": workflows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.get("/workflows/{workflow_id}")
async def get_workflow_endpoint(workflow_id: str):
    """Returns workflow metadata and latest checkpoint payload."""
    try:
        checkpoint = await workflow_manager.load_checkpoint(workflow_id)
        return {
            "workflow_id": workflow_id,
            "latest_checkpoint": checkpoint.model_dump()
        }
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))


@router.post("/workflows/{workflow_id}/resume")
async def resume_workflow_endpoint(workflow_id: str):
    """Restores execution state payload from latest checkpoint."""
    try:
        resumed_state = await workflow_manager.resume_workflow(workflow_id)
        return {
            "status": "success",
            "restored_state": {
                "workflow_id": resumed_state["workflow_id"],
                "goal": resumed_state["goal"].model_dump(),
                "plan": resumed_state["plan"].model_dump(),
                "progress_snapshot": resumed_state["progress_snapshot"].model_dump()
            }
        }
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))


@router.get("/checkpoints/{checkpoint_id}")
async def get_checkpoint_endpoint(checkpoint_id: str):
    """Returns detailed checkpoint payload by checkpoint_id."""
    # Find matching workflow for checkpoint_id
    workflows = await workflow_manager.list_workflows(limit=100)
    for wf in workflows:
        try:
            chk = await workflow_manager.load_checkpoint(wf["workflow_id"], checkpoint_id=checkpoint_id)
            return chk.model_dump()
        except ValueError:
            continue

    raise HTTPException(status_code=404, detail=f"Checkpoint '{checkpoint_id}' not found.")
