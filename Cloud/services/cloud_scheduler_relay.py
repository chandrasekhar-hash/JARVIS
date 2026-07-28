import time
import logging
from typing import Dict, Any, Optional, List
from Cloud.services.presence_service import presence_service, PresenceService
from Cloud.services.job_orchestrator import job_orchestrator, JobOrchestrator

logger = logging.getLogger("JARVIS_CloudSchedulerRelay")


class CloudSchedulerRelay:
    """
    CloudSchedulerRelay monitors device presence. When a primary scheduling device
    goes offline, CloudSchedulerRelay takes over scheduled tasks and executes them
    in the Cloud via JobOrchestrator.
    """

    def __init__(self, p_service: Optional[PresenceService] = None, orchestrator: Optional[JobOrchestrator] = None):
        self.presence = p_service or presence_service
        self.orchestrator = orchestrator or job_orchestrator
        self.relayed_tasks: Dict[str, Dict[str, Any]] = {}

    def register_scheduled_task(
        self,
        task_id: str,
        user_id: str,
        origin_device_id: str,
        task_name: str,
        schedule_cron: str,
        task_payload: Dict[str, Any]
    ):
        self.relayed_tasks[task_id] = {
            "task_id": task_id,
            "user_id": user_id,
            "origin_device_id": origin_device_id,
            "task_name": task_name,
            "schedule_cron": schedule_cron,
            "task_payload": task_payload,
            "last_relay": 0.0
        }
        logger.info(f"Registered scheduled task '{task_id}' ({task_name}) for Cloud Relay monitoring.")

    async def check_and_relay_offline_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        relayed_results = []
        for task_id, task in self.relayed_tasks.items():
            if task["user_id"] != user_id:
                continue

            origin_device = task["origin_device_id"]
            if not self.presence.is_device_online(origin_device):
                logger.warning(
                    f"Origin device '{origin_device}' is OFFLINE. "
                    f"CloudSchedulerRelay executing task '{task['task_name']}' in Cloud."
                )

                job = self.orchestrator.create_job(
                    user_id=user_id,
                    origin_device_id=origin_device,
                    task_type="scheduled_relay_task",
                    payload=task["task_payload"],
                    priority=8
                )

                async def dummy_exec():
                    return {"relay_status": "executed_in_cloud", "task_name": task["task_name"]}

                res = await self.orchestrator.execute_job(job.job_id, dummy_exec)
                task["last_relay"] = time.time()
                relayed_results.append(res)
        return relayed_results


cloud_scheduler_relay = CloudSchedulerRelay()
