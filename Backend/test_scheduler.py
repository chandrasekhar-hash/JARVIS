import unittest
import asyncio
import os
import time
from fastapi.testclient import TestClient

from autonomous.scheduler_models import JobType, JobStatus, ScheduleTrigger, ScheduledJob
from autonomous.schedule_parser import parse_natural_language_schedule, compute_next_run
from autonomous.scheduler_storage import SQLiteSchedulerStorage
from autonomous.task_registry import ProactiveTaskRegistry, task_registry
from autonomous.scheduler_engine import PersistentSchedulerEngine
from main import app

class TestPersistentAutonomousScheduler(unittest.TestCase):

    def setUp(self):
        self.test_db = "logs/test_jarvis_scheduler.db"
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass
        self.storage = SQLiteSchedulerStorage(db_path=self.test_db)
        self.client = TestClient(app)

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass

    def test_01_natural_language_parser(self):
        # 1. Interval
        t1 = parse_natural_language_schedule("Every 30 minutes")
        self.assertEqual(t1.job_type, JobType.INTERVAL)
        self.assertEqual(t1.interval_seconds, 1800)

        # 2. Daily morning
        t2 = parse_natural_language_schedule("Every morning at 8")
        self.assertEqual(t2.job_type, JobType.DAILY)
        self.assertEqual(t2.time_of_day, "08:00")

        # 3. Weekly Sunday
        t3 = parse_natural_language_schedule("Every Sunday at 6 PM")
        self.assertEqual(t3.job_type, JobType.WEEKLY)
        self.assertEqual(t3.day_of_week, 6)
        self.assertEqual(t3.time_of_day, "18:00")

        # 4. Next run calculation
        next_run = compute_next_run(t1)
        self.assertGreater(next_run, time.time())

    def test_02_sqlite_storage_persistence(self):
        trigger = parse_natural_language_schedule("Every 1 hour")
        job = ScheduledJob(
            job_id="test_job_1",
            task_name="system_diagnostics",
            description="Test storage job",
            trigger=trigger,
            enabled=True,
            next_run=time.time() + 3600
        )
        saved = self.storage.save_job(job)
        self.assertEqual(saved.job_id, "test_job_1")

        fetched = self.storage.get_job("test_job_1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.task_name, "system_diagnostics")
        self.assertEqual(fetched.status, JobStatus.SCHEDULED)

        all_jobs = self.storage.get_all_jobs()
        self.assertTrue(any(j.job_id == "test_job_1" for j in all_jobs))

    def test_03_task_registry_dynamic(self):
        reg = ProactiveTaskRegistry()
        executed = []

        async def mock_handler(**kwargs):
            executed.append(True)
            return {"status": "ok", "kwargs": kwargs}

        reg.register_task(
            name="custom_task",
            handler=mock_handler,
            description="Custom test task",
            default_schedule="Every 5 minutes",
            category="custom"
        )

        res = asyncio.run(reg.execute_task("custom_task", {"foo": "bar"}))
        self.assertEqual(res["status"], "ok")
        self.assertTrue(executed[0])

    def test_04_scheduler_engine_execution(self):
        engine = PersistentSchedulerEngine(storage=self.storage)
        
        # Save a test job
        trigger = parse_natural_language_schedule("Every 10 minutes")
        job = ScheduledJob(
            job_id="test_exec_job",
            task_name="system_diagnostics",
            description="Execution test",
            trigger=trigger,
            next_run=time.time() - 10  # Due now
        )
        self.storage.save_job(job)

        record = asyncio.run(engine.execute_job("test_exec_job"))
        self.assertEqual(record.status, JobStatus.COMPLETED)
        self.assertGreater(record.duration_seconds, 0)

        updated_job = self.storage.get_job("test_exec_job")
        self.assertEqual(updated_job.execution_count, 1)
        self.assertGreater(updated_job.next_run, time.time())

    def test_05_rest_api_endpoints(self):
        # 1. GET /api/scheduler/status
        r1 = self.client.get("/api/scheduler/status")
        self.assertEqual(r1.status_code, 200)
        self.assertIn("total_jobs", r1.json())

        # 2. GET /api/scheduler/jobs
        r2 = self.client.get("/api/scheduler/jobs")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("jobs", r2.json())

        # 3. POST /api/scheduler/jobs
        r3 = self.client.post("/api/scheduler/jobs", json={
            "task_name": "provider_health_check",
            "schedule_expression": "Every 15 minutes",
            "description": "API Test Job"
        })
        self.assertEqual(r3.status_code, 200)
        new_job_id = r3.json()["job"]["job_id"]

        # 4. POST /api/scheduler/jobs/{id}/run
        r4 = self.client.post(f"/api/scheduler/jobs/{new_job_id}/run")
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()["status"], "success")

        # 5. GET /api/scheduler/jobs/{id}/history
        r5 = self.client.get(f"/api/scheduler/jobs/{new_job_id}/history")
        self.assertEqual(r5.status_code, 200)
        self.assertGreater(len(r5.json()["history"]), 0)

        # 6. DELETE /api/scheduler/jobs/{id}
        r6 = self.client.delete(f"/api/scheduler/jobs/{new_job_id}")
        self.assertEqual(r6.status_code, 200)


if __name__ == "__main__":
    unittest.main()
