import time
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("JARVIS_JobOrchestrator")


class RemoteJob(BaseModel):
    job_id: str
    user_id: str
    origin_device_id: str
    execution_node_id: Optional[str] = None
    task_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 5
    status: str = "QUEUED"  # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 60.0
    trace_id: str
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    error_message: Optional[str] = None


class JobOrchestrator:
    """
    Distributed Job Orchestrator managing job lifecycle (QUEUED -> RUNNING -> COMPLETED / FAILED / CANCELLED),
    priority queues, retries, timeouts, and execution cancellation.
    """

    def __init__(self):
        # job_id -> RemoteJob
        self.jobs: Dict[str, RemoteJob] = {}

    def create_job(
        self,
        user_id: str,
        origin_device_id: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 5,
        max_retries: int = 3,
        timeout_seconds: float = 60.0,
        trace_id: Optional[str] = None
    ) -> RemoteJob:
        trace_id = trace_id or f"trc_job_{uuid.uuid4().hex[:12]}"
        job = RemoteJob(
            job_id=f"job_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            origin_device_id=origin_device_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            trace_id=trace_id
        )
        self.jobs[job.job_id] = job
        logger.info(f"[{trace_id}] Job '{job.job_id}' created (task: '{task_type}', priority: {priority}). Status: QUEUED")
        return job

    def transition_state(self, job_id: str, new_status: str, execution_node: Optional[str] = None, error: Optional[str] = None) -> Optional[RemoteJob]:
        job = self.jobs.get(job_id)
        if not job:
            return None

        old_status = job.status
        job.status = new_status
        job.updated_at = time.time()
        if execution_node:
            job.execution_node_id = execution_node
        if error:
            job.error_message = error

        logger.info(f"[{job.trace_id}] Job '{job_id}' transition: {old_status} -> {new_status}")
        return job

    def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job and job.status in ["QUEUED", "RUNNING"]:
            self.transition_state(job_id, "CANCELLED")
            return True
        return False

    async def execute_job(self, job_id: str, execution_func) -> Dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")

        self.transition_state(job_id, "RUNNING", execution_node="cloud_gateway_node_1")

        try:
            res = await asyncio.wait_for(execution_func(), timeout=job.timeout_seconds)
            self.transition_state(job_id, "COMPLETED")
            return {"job_id": job_id, "status": "COMPLETED", "result": res}
        except asyncio.TimeoutError:
            err_msg = f"Job execution timed out after {job.timeout_seconds}s."
            logger.error(f"[{job.trace_id}] {err_msg}")
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                self.transition_state(job_id, "QUEUED", error=err_msg)
                logger.info(f"[{job.trace_id}] Retrying job '{job_id}' (Attempt #{job.retry_count}/{job.max_retries})...")
                return await self.execute_job(job_id, execution_func)
            else:
                self.transition_state(job_id, "FAILED", error=err_msg)
                return {"job_id": job_id, "status": "FAILED", "error": err_msg}
        except Exception as e:
            err_msg = str(e)
            logger.error(f"[{job.trace_id}] Error executing job '{job_id}': {e}")
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                self.transition_state(job_id, "QUEUED", error=err_msg)
                return await self.execute_job(job_id, execution_func)
            else:
                self.transition_state(job_id, "FAILED", error=err_msg)
                return {"job_id": job_id, "status": "FAILED", "error": err_msg}

    def get_job(self, job_id: str) -> Optional[RemoteJob]:
        return self.jobs.get(job_id)


job_orchestrator = JobOrchestrator()
