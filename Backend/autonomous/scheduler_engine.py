import asyncio
import time
import uuid
import traceback
from typing import List, Dict, Any, Optional, Set
from autonomous.scheduler_models import (
    ScheduledJob,
    JobExecutionRecord,
    JobStatus,
    JobType,
    SchedulerMetrics
)
from autonomous.schedule_parser import parse_natural_language_schedule, compute_next_run
from autonomous.scheduler_storage import scheduler_storage, SQLiteSchedulerStorage
from autonomous.task_registry import task_registry
from tools.telemetry import log_structured, backend_log, telemetry_manager

class PersistentSchedulerEngine:
    """
    Production-ready Persistent Autonomous Scheduler Engine for J.A.R.V.I.S.
    Executes proactive background intelligence tasks, manages retries with backoff,
    prevents duplicate/overlapping executions, and persists schedules across restarts.
    """

    def __init__(self, storage: Optional[SQLiteSchedulerStorage] = None):
        self.storage = storage or scheduler_storage
        self.is_running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._running_jobs: Set[str] = set()
        self._start_time: float = 0.0

    def start(self) -> None:
        """
        Starts the persistent scheduler engine background loop.
        """
        if self.is_running:
            return
            
        self.is_running = True
        self._start_time = time.time()
        self._ensure_default_jobs()
        
        # Launch background loop task in current asyncio loop
        try:
            loop = asyncio.get_running_loop()
            self._loop_task = loop.create_task(self._scheduler_loop())
            log_structured(backend_log, "INFO", "[SchedulerEngine] Started autonomous background scheduler loop")
        except RuntimeError:
            log_structured(backend_log, "WARNING", "[SchedulerEngine] No running asyncio loop available to start scheduler loop immediately.")

    def stop(self) -> None:
        """
        Gracefully stops the scheduler engine loop.
        """
        if not self.is_running:
            return
            
        self.is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None
        log_structured(backend_log, "INFO", "[SchedulerEngine] Stopped autonomous scheduler loop")

    def _ensure_default_jobs(self) -> None:
        """
        Ensures default task definitions registered in task_registry exist in persistent storage.
        """
        existing = {j.task_name: j for j in self.storage.get_all_jobs()}
        tasks = task_registry.get_all_tasks()
        
        for task_def in tasks:
            if task_def.name not in existing:
                trigger = parse_natural_language_schedule(task_def.default_schedule or "Every day at 08:00")
                next_run = compute_next_run(trigger)
                job = ScheduledJob(
                    job_id=f"job_{task_def.name}",
                    task_name=task_def.name,
                    description=task_def.description,
                    trigger=trigger,
                    enabled=task_def.enabled,
                    next_run=next_run,
                    status=JobStatus.SCHEDULED
                )
                self.storage.save_job(job)
                log_structured(backend_log, "INFO", f"[SchedulerEngine] Provisioned default job '{job.job_id}' (next run: {time.ctime(next_run)})")

    async def _scheduler_loop(self) -> None:
        """
        Continuous background loop evaluating due jobs.
        """
        while self.is_running:
            try:
                now = time.time()
                jobs = self.storage.get_all_jobs()
                
                for job in jobs:
                    if not self.is_running:
                        break
                        
                    if not job.enabled:
                        continue
                        
                    if job.job_id in self._running_jobs:
                        continue
                        
                    if job.next_run <= now:
                        # Schedule job execution concurrently without blocking loop
                        asyncio.create_task(self.execute_job(job.job_id))
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_structured(backend_log, "ERROR", f"[SchedulerEngine] Exception in scheduler loop: {str(e)}")
                
            await asyncio.sleep(3)

    async def execute_job(self, job_id: str, is_manual_trigger: bool = False) -> JobExecutionRecord:
        """
        Executes a scheduled job with concurrency protection, timeout enforcement,
        and exponential backoff retry handling.
        """
        job = self.storage.get_job(job_id)
        if not job:
            raise ValueError(f"Scheduled job '{job_id}' not found.")
            
        if job_id in self._running_jobs and not is_manual_trigger:
            log_structured(backend_log, "WARNING", f"[SchedulerEngine] Job '{job_id}' is already running. Skipping execution.")
            return JobExecutionRecord(
                execution_id=f"exec_{uuid.uuid4().hex[:8]}",
                job_id=job_id,
                task_name=job.task_name,
                start_time=time.time(),
                status=JobStatus.SKIPPED if hasattr(JobStatus, "SKIPPED") else JobStatus.RUNNING,
                error_message="Skipped due to concurrent execution."
            )
            
        self._running_jobs.add(job_id)
        job.status = JobStatus.RUNNING
        self.storage.save_job(job)
        
        exec_id = f"exec_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        record = JobExecutionRecord(
            execution_id=exec_id,
            job_id=job_id,
            task_name=job.task_name,
            start_time=start_time,
            status=JobStatus.RUNNING,
            retry_attempt=job.failure_count
        )
        self.storage.log_execution(record)
        log_structured(backend_log, "INFO", f"[SchedulerEngine] Job '{job_id}' ({job.task_name}) started execution.")
        
        error_msg = None
        result_summary = None
        success = False
        
        try:
            # Enforce timeout protection
            res = await asyncio.wait_for(
                task_registry.execute_task(job.task_name, job.params),
                timeout=float(job.timeout_seconds)
            )
            success = True
            result_summary = str(res)
        except asyncio.TimeoutError:
            error_msg = f"Job execution timed out after {job.timeout_seconds} seconds."
            log_structured(backend_log, "ERROR", f"[SchedulerEngine] Job '{job_id}' timeout: {error_msg}")
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            log_structured(backend_log, "ERROR", f"[SchedulerEngine] Job '{job_id}' failed: {error_msg}\n{traceback.format_exc()}")
            
        end_time = time.time()
        duration = round(end_time - start_time, 3)
        telemetry_manager.record_latency(f"scheduler_job_{job.task_name}", duration)
        
        if success:
            job.status = JobStatus.COMPLETED
            job.last_run = start_time
            job.execution_count += 1
            job.failure_count = 0  # Reset failure count on success
            
            if job.trigger.job_type == JobType.ONE_TIME:
                job.enabled = False
            else:
                job.next_run = compute_next_run(job.trigger, base_time=end_time)
                
            record.status = JobStatus.COMPLETED
            record.end_time = end_time
            record.duration_seconds = duration
            record.result_summary = result_summary
            
            log_structured(backend_log, "INFO", f"[SchedulerEngine] Job '{job_id}' completed successfully in {duration}s. Next run: {time.ctime(job.next_run)}")
        else:
            job.failure_count += 1
            record.status = JobStatus.FAILED
            record.end_time = end_time
            record.duration_seconds = duration
            record.error_message = error_msg
            
            if job.failure_count <= job.max_retries:
                # Exponential backoff retry calculation
                backoff_sec = int((job.retry_backoff_factor ** (job.failure_count - 1)) * 10)
                job.next_run = end_time + backoff_sec
                job.status = JobStatus.SCHEDULED
                log_structured(backend_log, "WARNING", f"[SchedulerEngine] Retrying job '{job_id}' (attempt {job.failure_count}/{job.max_retries}) in {backoff_sec}s.")
            else:
                job.status = JobStatus.FAILED
                job.next_run = compute_next_run(job.trigger, base_time=end_time)
                log_structured(backend_log, "ERROR", f"[SchedulerEngine] Job '{job_id}' failed max retries ({job.max_retries}). Next regular run: {time.ctime(job.next_run)}")

        self.storage.save_job(job)
        self.storage.log_execution(record)
        self.running_jobs_remove(job_id)
        return record

    def running_jobs_remove(self, job_id: str) -> None:
        self._running_jobs.discard(job_id)

    def pause_job(self, job_id: str) -> ScheduledJob:
        job = self.storage.get_job(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")
        job.enabled = False
        job.status = JobStatus.PAUSED
        self.storage.save_job(job)
        log_structured(backend_log, "INFO", f"[SchedulerEngine] Paused job '{job_id}'")
        return job

    def resume_job(self, job_id: str) -> ScheduledJob:
        job = self.storage.get_job(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")
        job.enabled = True
        job.status = JobStatus.SCHEDULED
        job.next_run = compute_next_run(job.trigger)
        self.storage.save_job(job)
        log_structured(backend_log, "INFO", f"[SchedulerEngine] Resumed job '{job_id}' (next run: {time.ctime(job.next_run)})")
        return job

    def get_status_report(self) -> Dict[str, Any]:
        metrics = self.storage.get_metrics()
        metrics.is_running = self.is_running
        metrics.running_jobs = len(self._running_jobs)
        if self._start_time > 0:
            metrics.scheduler_uptime_seconds = round(time.time() - self._start_time, 1)
        return metrics.model_dump()


scheduler_engine = PersistentSchedulerEngine()
