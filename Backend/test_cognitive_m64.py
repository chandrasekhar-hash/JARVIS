import os
import sys
import time
import asyncio
import unittest

# Ensure Backend root is in import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive import (
    PostExecutionReflectionEngine,
    ReflectionReport,
    GoalOutcome,
    CognitiveAssessment,
    StrategyType,
    RiskLevel,
    ExperienceRepository,
)
from memory.storage.sqlite_provider import SQLiteMemoryStorageProvider

TEST_DB_PATH = "logs/test_cognitive_m64.db"


def cleanup_test_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


class TestPostExecutionReflectionEngine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        cleanup_test_db()
        self.storage = SQLiteMemoryStorageProvider(db_path=TEST_DB_PATH)
        self.exp_repo = ExperienceRepository(memory_storage=self.storage)
        self.reflection_engine = PostExecutionReflectionEngine(exp_repo=self.exp_repo)

    async def asyncTearDown(self):
        cleanup_test_db()

    async def test_successful_workflow_reflection(self):
        start = time.time()
        task_results = [
            {"task_name": "Task 1", "tool_name": "app_open", "status": "completed", "duration": 0.5},
            {"task_name": "Task 2", "tool_name": "browser_open_url", "status": "completed", "duration": 0.8}
        ]
        assessment = CognitiveAssessment(
            goal_id="g_success",
            confidence_score=0.90,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="Simple open command."
        )

        report = await self.reflection_engine.reflect_on_workflow(
            goal_id="g_success",
            workflow_id="wf_100",
            raw_outcome="completed",
            total_execution_time_sec=1.3,
            task_results=task_results,
            assessment=assessment
        )
        elapsed_ms = (time.time() - start) * 1000.0

        self.assertIsInstance(report, ReflectionReport)
        self.assertEqual(report.outcome, GoalOutcome.SUCCESS)
        self.assertEqual(report.confidence_adjustment, 0.05)
        self.assertIn("app_open", report.tool_effectiveness_scores)
        self.assertEqual(report.tool_effectiveness_scores["app_open"], 1.0)
        self.assertTrue(len(report.success_factors) >= 1)
        self.assertTrue(len(report.lessons_learned) >= 1)
        self.assertIsNotNone(report.suggested_template_id)
        self.assertLess(elapsed_ms, 100.0, "Simple reflection should complete in <100ms")

        # Verify template persisted in ExperienceRepository
        tmpl = await self.exp_repo.get_workflow_template(report.suggested_template_id)
        self.assertIsNotNone(tmpl)

    async def test_failed_workflow_reflection_and_overestimation_penalty(self):
        start = time.time()
        task_results = [
            {"task_name": "Task 1", "tool_name": "fs_file_operation", "status": "failed", "error": "PermissionError: Access Denied", "duration": 0.2}
        ]
        assessment = CognitiveAssessment(
            goal_id="g_failed",
            confidence_score=0.85,  # High confidence before execution
            risk_level=RiskLevel.MEDIUM,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="Expected easy file edit."
        )

        report = await self.reflection_engine.reflect_on_workflow(
            goal_id="g_failed",
            workflow_id="wf_200",
            raw_outcome="failed",
            total_execution_time_sec=0.2,
            task_results=task_results,
            assessment=assessment,
            errors=["PermissionError: Access Denied"]
        )
        elapsed_ms = (time.time() - start) * 1000.0

        self.assertEqual(report.outcome, GoalOutcome.FAILED)
        self.assertEqual(report.confidence_adjustment, -0.35, "Overestimated confidence should result in -0.35 adjustment")
        self.assertTrue(len(report.failure_causes) >= 1)
        self.assertIn("PermissionError", report.failure_causes[0])
        self.assertTrue(len(report.recommended_improvements) >= 1)
        self.assertLess(elapsed_ms, 500.0, "Complex reflection should complete in <500ms")

        # Verify FailurePattern persisted in ExperienceRepository
        patterns = await self.exp_repo.get_failure_patterns("fs_file_operation")
        self.assertTrue(len(patterns) >= 1)

    async def test_partial_success_reflection(self):
        task_results = [
            {"task_name": "Task 1", "tool_name": "browser_open_url", "status": "completed", "duration": 0.4},
            {"task_name": "Task 2", "tool_name": "browser_click_link", "status": "failed", "error": "Element not found", "duration": 1.2}
        ]
        report = await self.reflection_engine.reflect_on_workflow(
            goal_id="g_partial",
            workflow_id="wf_300",
            raw_outcome="completed",
            total_execution_time_sec=1.6,
            task_results=task_results
        )

        self.assertEqual(report.outcome, GoalOutcome.PARTIAL_SUCCESS)
        self.assertEqual(report.confidence_adjustment, -0.10)
        self.assertEqual(report.execution_statistics["completed_tasks"], 1)
        self.assertEqual(report.execution_statistics["failed_tasks"], 1)

    async def test_cancelled_workflow_reflection(self):
        report = await self.reflection_engine.reflect_on_workflow(
            goal_id="g_cancel",
            workflow_id="wf_400",
            raw_outcome="cancelled",
            total_execution_time_sec=0.5
        )
        self.assertEqual(report.outcome, GoalOutcome.CANCELLED)
        self.assertEqual(report.confidence_adjustment, -0.25)

    async def test_missing_execution_data_fallback(self):
        # Should gracefully return a valid ReflectionReport without crashing callers
        report = await self.reflection_engine.reflect_on_workflow(
            goal_id="",
            workflow_id="",
            raw_outcome="unknown",
            total_execution_time_sec=-1.0
        )
        self.assertIsInstance(report, ReflectionReport)
        self.assertEqual(report.total_execution_time_sec, 0.0)
        self.assertEqual(report.outcome, GoalOutcome.CANCELLED)


if __name__ == "__main__":
    unittest.main()
