import os
import sys
import time
import asyncio
import unittest

# Ensure Backend root is in import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive import (
    AdaptivePlannerBridge,
    AdaptationPlan,
    CognitiveAssessment,
    StrategyType,
    RiskLevel,
    GoalOutcome,
    ReflectionReport,
    WorkflowTemplate,
    FailurePattern,
    ExperienceRepository,
    CognitivePolicyEngine,
)
from memory.storage.sqlite_provider import SQLiteMemoryStorageProvider

TEST_DB_PATH = "logs/test_cognitive_m65.db"


def cleanup_test_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


class TestAdaptivePlannerBridge(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        cleanup_test_db()
        self.storage = SQLiteMemoryStorageProvider(db_path=TEST_DB_PATH)
        self.exp_repo = ExperienceRepository(memory_storage=self.storage)
        self.policy_engine = CognitivePolicyEngine()
        self.bridge = AdaptivePlannerBridge(
            policy_engine=self.policy_engine,
            exp_repo=self.exp_repo
        )

    async def asyncTearDown(self):
        cleanup_test_db()

    async def test_simple_plan_adaptation(self):
        start = time.time()
        assessment = CognitiveAssessment(
            goal_id="g_simple_adapt",
            confidence_score=0.95,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="Simple web search goal."
        )
        current_plan = [
            {"task_name": "Open Browser", "tool_name": "browser_open_url"},
            {"task_name": "Search Query", "tool_name": "browser_search"}
        ]

        plan = await self.bridge.adapt_execution_plan(
            goal_id="g_simple_adapt",
            assessment=assessment,
            current_plan=current_plan
        )
        elapsed_ms = (time.time() - start) * 1000.0

        self.assertIsInstance(plan, AdaptationPlan)
        self.assertEqual(plan.goal_id, "g_simple_adapt")
        self.assertEqual(plan.adapted_strategy, StrategyType.DIRECT_EXECUTION)
        self.assertTrue(plan.approved)
        self.assertTrue(len(plan.recommended_task_order) >= 2)
        self.assertLess(elapsed_ms, 100.0, "Simple adaptation should take <100ms")

    async def test_failure_history_strategy_elevation_and_decomposition(self):
        start = time.time()
        # Seed failure patterns
        fp1 = FailurePattern(error_signature="fs_file_operation", root_cause="Access Denied", suggested_workaround="Check perms")
        fp2 = FailurePattern(error_signature="fs_file_operation", root_cause="File locked", suggested_workaround="Close app")
        await self.exp_repo.store_failure_pattern(fp1)
        await self.exp_repo.store_failure_pattern(fp2)

        assessment = CognitiveAssessment(
            goal_id="g_elevate",
            confidence_score=0.75,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="File modification task."
        )
        current_plan = [
            {"task_name": "Edit File", "tool_name": "fs_file_operation"}
        ]

        plan = await self.bridge.adapt_execution_plan(
            goal_id="g_elevate",
            assessment=assessment,
            current_plan=current_plan
        )
        elapsed_ms = (time.time() - start) * 1000.0

        # Strategy should be elevated to HIERARCHICAL_DECOMPOSITION due to failure patterns
        self.assertEqual(plan.adapted_strategy, StrategyType.HIERARCHICAL_DECOMPOSITION)
        self.assertTrue(len(plan.decomposition_changes) >= 1)
        self.assertIn("Verify Environment", plan.recommended_task_order[0])
        self.assertGreater(plan.retry_policy["max_retries"], self.policy_engine.config.MAX_TASK_RETRIES)
        self.assertLess(elapsed_ms, 500.0, "Complex adaptation should take <500ms")

    async def test_parallelization_recommendations(self):
        assessment = CognitiveAssessment(
            goal_id="g_parallel",
            confidence_score=0.85,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.HIERARCHICAL_DECOMPOSITION,
            reasoning_summary="Gather info."
        )
        current_plan = [
            {"task_name": "Read config file", "tool_name": "fs_read_file"},
            {"task_name": "Search documentation", "tool_name": "browser_search"}
        ]

        plan = await self.bridge.adapt_execution_plan(
            goal_id="g_parallel",
            assessment=assessment,
            current_plan=current_plan
        )

        self.assertTrue(len(plan.parallelisation_recommendations) >= 1)
        self.assertIn("parallel", plan.parallelisation_recommendations[0].lower())

    async def test_policy_rejection_for_unsafe_strategy(self):
        assessment = CognitiveAssessment(
            goal_id="g_unsafe",
            confidence_score=0.50,
            risk_level=RiskLevel.HIGH,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="High risk action."
        )
        plan = await self.bridge.adapt_execution_plan(
            goal_id="g_unsafe",
            assessment=assessment,
            current_plan=[{"task_name": "Delete directory", "tool_name": "fs_file_operation"}]
        )

        self.assertFalse(plan.approved, "Direct execution for HIGH risk must be rejected by policy")

    async def test_empty_plan_fallback(self):
        assessment = CognitiveAssessment(
            goal_id="g_empty",
            confidence_score=0.80,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="No tasks."
        )
        plan = await self.bridge.adapt_execution_plan(
            goal_id="g_empty",
            assessment=assessment,
            current_plan=[]
        )
        self.assertIsInstance(plan, AdaptationPlan)
        self.assertTrue(plan.approved)


if __name__ == "__main__":
    unittest.main()
