import os
import sys
import asyncio
import unittest

# Ensure Backend root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive import (
    WorkflowTemplate,
    FailurePattern,
    ReflectionReport,
    CognitiveAssessment,
    StrategyType,
    RiskLevel,
    GoalOutcome,
    ExperienceRepository,
)
from memory.storage.sqlite_provider import SQLiteMemoryStorageProvider

TEST_DB_PATH = "logs/test_cognitive_m62.db"


def cleanup_test_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


class TestExperienceRepository(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        cleanup_test_db()
        self.storage = SQLiteMemoryStorageProvider(db_path=TEST_DB_PATH)
        self.repo = ExperienceRepository(memory_storage=self.storage)

    async def asyncTearDown(self):
        cleanup_test_db()

    async def test_workflow_template_crud(self):
        tmpl = WorkflowTemplate(
            goal_pattern="Build React Application",
            recommended_tasks=[{"name": "Init Vite"}, {"name": "Install Deps"}, {"name": "Build"}]
        )
        stored_id = await self.repo.store_workflow_template(tmpl)
        self.assertEqual(stored_id, tmpl.template_id)

        fetched = await self.repo.get_workflow_template(tmpl.template_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.goal_pattern, "Build React Application")
        self.assertEqual(len(fetched.recommended_tasks), 3)

    async def test_failure_pattern_crud(self):
        fail_pat = FailurePattern(
            error_signature="PermissionError: File lock held",
            root_cause="Another process holds file handle",
            suggested_workaround="Wait for handle release or retry"
        )
        stored_id = await self.repo.store_failure_pattern(fail_pat)
        self.assertEqual(stored_id, fail_pat.pattern_id)

        fetched = await self.repo.get_failure_pattern(fail_pat.pattern_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.error_signature, "PermissionError: File lock held")

    async def test_reflection_and_assessment_crud(self):
        refl = ReflectionReport(
            goal_id="g_100",
            workflow_id="wf_200",
            outcome=GoalOutcome.SUCCESS,
            total_execution_time_sec=3.2,
            lessons_learned=["Execution was fast."]
        )
        r_id = await self.repo.store_reflection(refl)
        self.assertEqual(r_id, refl.reflection_id)

        assess = CognitiveAssessment(
            goal_id="g_100",
            confidence_score=0.92,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="Low risk direct query."
        )
        a_id = await self.repo.store_assessment(assess)
        self.assertEqual(a_id, assess.assessment_id)

        fetched_refl = await self.repo.get_reflection(refl.reflection_id)
        self.assertIsNotNone(fetched_refl)
        self.assertEqual(fetched_refl.outcome, GoalOutcome.SUCCESS)

        fetched_assess = await self.repo.get_assessment(assess.assessment_id)
        self.assertIsNotNone(fetched_assess)
        self.assertEqual(fetched_assess.confidence_score, 0.92)

    async def test_search_and_ranking(self):
        tmpl1 = WorkflowTemplate(goal_pattern="Organize Downloads folder", success_count=5)
        tmpl2 = WorkflowTemplate(goal_pattern="Build React project", success_count=10)
        await self.repo.store_workflow_template(tmpl1)
        await self.repo.store_workflow_template(tmpl2)

        results = await self.repo.search_similar_experiences(query_text="Build React App", limit=5)
        self.assertTrue(len(results) >= 1)
        self.assertIn("React", results[0]["title"])

        best = await self.repo.get_best_matching_template("Build React Application")
        self.assertIsNotNone(best)
        self.assertEqual(best.goal_pattern, "Build React project")

    async def test_statistics_and_counters(self):
        tmpl = WorkflowTemplate(goal_pattern="Run test suite", success_count=1, average_duration_sec=10.0)
        await self.repo.store_workflow_template(tmpl)

        # Update success stats
        updated_ok = await self.repo.update_success_statistics(tmpl.template_id, execution_time_sec=20.0)
        self.assertTrue(updated_ok)

        fetched = await self.repo.get_workflow_template(tmpl.template_id)
        self.assertEqual(fetched.success_count, 2)
        self.assertEqual(fetched.average_duration_sec, 15.0)

        # Increment reuse counter
        reuse_ok = await self.repo.increment_reuse_count(tmpl.template_id)
        self.assertTrue(reuse_ok)

        fetched2 = await self.repo.get_workflow_template(tmpl.template_id)
        self.assertEqual(fetched2.success_count, 3)

    async def test_failure_patterns_query_and_stats(self):
        fp = FailurePattern(error_signature="TimeoutError: Socket closed", root_cause="Network timeout", suggested_workaround="Retry request")
        await self.repo.store_failure_pattern(fp)

        pats = await self.repo.get_failure_patterns(error_signature="TimeoutError")
        self.assertEqual(len(pats), 1)
        self.assertEqual(pats[0].pattern_id, fp.pattern_id)

        update_ok = await self.repo.update_failure_statistics(fp.pattern_id)
        self.assertTrue(update_ok)

        fp_updated = await self.repo.get_failure_pattern(fp.pattern_id)
        self.assertEqual(fp_updated.occurrence_count, 2)

    async def test_delete_experience(self):
        tmpl = WorkflowTemplate(goal_pattern="Temporary workflow")
        await self.repo.store_workflow_template(tmpl)

        deleted = await self.repo.delete_experience(tmpl.template_id)
        self.assertTrue(deleted)

        fetched = await self.repo.get_workflow_template(tmpl.template_id)
        self.assertIsNone(fetched)

    async def test_missing_or_corrupted_experience_handling(self):
        # Non-existent ID return None cleanly without crashing
        self.assertIsNone(await self.repo.get_workflow_template("non_existent_id"))
        self.assertIsNone(await self.repo.get_failure_pattern("non_existent_id"))
        self.assertFalse(await self.repo.update_success_statistics("non_existent_id", 5.0))
        self.assertFalse(await self.repo.update_failure_statistics("non_existent_id"))


if __name__ == "__main__":
    unittest.main()
