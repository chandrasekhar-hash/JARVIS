import os
import sys
import time
import asyncio
import unittest

# Ensure Backend root is in import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive import (
    MultiGoalCoordinator,
    GoalExecutionPlan,
    CognitiveAssessment,
    StrategyType,
    RiskLevel,
    CognitivePolicyEngine,
)


class TestMultiGoalCoordinator(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.policy_engine = CognitivePolicyEngine()
        self.coordinator = MultiGoalCoordinator(policy_engine=self.policy_engine)

    async def test_small_goal_set_coordination(self):
        start = time.time()
        a1 = CognitiveAssessment(
            goal_id="g_search",
            confidence_score=0.90,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="Search documentation on browser"
        )
        a2 = CognitiveAssessment(
            goal_id="g_build",
            confidence_score=0.85,
            risk_level=RiskLevel.MEDIUM,
            recommended_strategy=StrategyType.HIERARCHICAL_DECOMPOSITION,
            reasoning_summary="Build project files in folder"
        )

        plan = await self.coordinator.coordinate_goals([a1, a2])
        elapsed_ms = (time.time() - start) * 1000.0

        self.assertIsInstance(plan, GoalExecutionPlan)
        self.assertTrue(plan.approved)
        self.assertEqual(len(plan.ordered_goals), 2)
        self.assertTrue(len(plan.execution_batches) >= 1)
        self.assertLess(elapsed_ms, 100.0, "Sub-3 goals coordination should finish in <100ms")

    async def test_circular_dependency_rejection(self):
        a1 = CognitiveAssessment(
            goal_id="g_alpha",
            confidence_score=0.80,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="Alpha task"
        )
        a2 = CognitiveAssessment(
            goal_id="g_beta",
            confidence_score=0.80,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="Beta task"
        )
        # Inject circular dependency via metadata
        object.__setattr__(a1, "metadata", {"depends_on": ["g_beta"]})
        object.__setattr__(a2, "metadata", {"depends_on": ["g_alpha"]})

        plan = await self.coordinator.coordinate_goals([a1, a2])

        self.assertTrue("g_alpha" in plan.blocked_goals or "g_beta" in plan.blocked_goals)
        self.assertTrue(len(plan.blocked_goals) >= 1)

    async def test_resource_conflict_batch_separation(self):
        a1 = CognitiveAssessment(
            goal_id="g_file1",
            confidence_score=0.80,
            risk_level=RiskLevel.MEDIUM,
            recommended_strategy=StrategyType.HIERARCHICAL_DECOMPOSITION,
            reasoning_summary="Modify file in directory"
        )
        a2 = CognitiveAssessment(
            goal_id="g_file2",
            confidence_score=0.80,
            risk_level=RiskLevel.MEDIUM,
            recommended_strategy=StrategyType.HIERARCHICAL_DECOMPOSITION,
            reasoning_summary="Delete folder in directory"
        )

        plan = await self.coordinator.coordinate_goals([a1, a2])

        # Concurrent write tasks with fs_lock should be separated into distinct batches
        self.assertGreaterEqual(len(plan.execution_batches), 2)

    async def test_policy_concurrency_limit_enforcement(self):
        assessments = [
            CognitiveAssessment(
                goal_id=f"g_batch_{i}",
                confidence_score=0.80 + (i * 0.02),
                risk_level=RiskLevel.LOW,
                recommended_strategy=StrategyType.DIRECT_EXECUTION,
                reasoning_summary=f"Task {i}"
            )
            for i in range(5)  # 5 goals exceeds MAX_CONCURRENT_GOALS (3)
        ]

        plan = await self.coordinator.coordinate_goals(assessments)

        self.assertEqual(len(plan.ordered_goals), 3)
        self.assertEqual(len(plan.blocked_goals), 2)

    async def test_ten_goals_performance_benchmark(self):
        start = time.time()
        assessments = [
            CognitiveAssessment(
                goal_id=f"g_bench_{i}",
                confidence_score=0.85,
                risk_level=RiskLevel.LOW,
                recommended_strategy=StrategyType.DIRECT_EXECUTION,
                reasoning_summary=f"Benchmark task {i}"
            )
            for i in range(10)
        ]
        # Allow max concurrent for benchmark test
        self.policy_engine.config.MAX_CONCURRENT_GOALS = 15

        plan = await self.coordinator.coordinate_goals(assessments)
        elapsed_ms = (time.time() - start) * 1000.0

        self.assertEqual(len(plan.ordered_goals), 10)
        self.assertLess(elapsed_ms, 500.0, "10-goal coordination should finish in <500ms")

    async def test_empty_goals_input(self):
        plan = await self.coordinator.coordinate_goals([])
        self.assertIsInstance(plan, GoalExecutionPlan)
        self.assertEqual(len(plan.ordered_goals), 0)
        self.assertTrue(plan.approved)


if __name__ == "__main__":
    unittest.main()
