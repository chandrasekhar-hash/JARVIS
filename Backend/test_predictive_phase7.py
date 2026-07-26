import os
import sys
import time
import asyncio
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unified_context.models import CognitiveContext, ContextChunk, ContextSource, ContextPriority
from predictive.models import (
    GoalPrediction,
    IntentPrediction,
    WorkflowPrediction,
    Suggestion,
    PredictionResult,
    PredictionCandidate,
)
from predictive.intent_forecaster import IntentForecaster
from predictive.workflow_anticipator import WorkflowAnticipator
from predictive.confidence_ranker import ConfidenceRanker
from predictive.proactive_suggester import ProactiveSuggester
from predictive.engine import PredictiveGoalEngine
from brain.event_bus import EventBus


class TestPredictivePhase7(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.context = CognitiveContext(
            user_id="u_pred",
            chunks=[
                ContextChunk(
                    source=ContextSource.USER_MODEL,
                    provider_id="p_user",
                    content="Preferred Tools: vscode, python. Explicit Preferences: editor=VS Code",
                    priority=ContextPriority.HIGH,
                ),
                ContextChunk(
                    source=ContextSource.ENVIRONMENT,
                    provider_id="p_env",
                    content="Active App: Visual Studio Code",
                    priority=ContextPriority.LOW,
                ),
            ],
            formatted_prompt_context="Active App: Visual Studio Code. Working on python script editor repo. Explicit Preferences: editor=VS Code",
            sources_included=[ContextSource.USER_MODEL, ContextSource.ENVIRONMENT],
        )

    async def test_intent_forecasting(self):
        forecaster = IntentForecaster()
        intents = forecaster.forecast_intents(self.context)

        self.assertGreater(len(intents), 0)
        self.assertEqual(intents[0].intent_category, "code_development")
        self.assertGreater(intents[0].probability, 0.5)

        candidates = forecaster.generate_candidates(intents, self.context)
        self.assertGreater(len(candidates), 0)
        self.assertIn("Run automated tests", candidates[0].goal_description)

    async def test_workflow_anticipation(self):
        forecaster = IntentForecaster()
        anticipator = WorkflowAnticipator()

        intents = forecaster.forecast_intents(self.context)
        workflows = anticipator.anticipate_workflows(intents, self.context)

        self.assertGreater(len(workflows), 0)
        self.assertIn("view_file", workflows[0].predicted_tool_sequence)

    async def test_confidence_ranking_and_explainability_sla(self):
        ranker = ConfidenceRanker()
        candidates = [
            PredictionCandidate(goal_description="Fix bug in python code", intent_category="code_development", raw_score=0.85, signals=["python", "vscode"])
        ]

        start = time.perf_counter()
        predictions = ranker.score_and_rank(candidates, self.context)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # SLA < 20 ms
        self.assertLess(elapsed_ms, 20.0)
        self.assertEqual(len(predictions), 1)
        self.assertGreater(predictions[0].confidence, 0.70)
        self.assertIsNotNone(predictions[0].explanation)
        self.assertGreater(len(predictions[0].explanation.trigger_signals), 0)

    async def test_proactive_suggestion_generation(self):
        suggester = ProactiveSuggester(default_min_threshold=0.80)
        ranker = ConfidenceRanker()
        candidates = [
            PredictionCandidate(goal_description="Run unit test suite", intent_category="code_development", raw_score=0.90, signals=["python", "vscode"])
        ]
        predictions = ranker.score_and_rank(candidates, self.context)

        start = time.perf_counter()
        suggestions = suggester.generate_suggestions(predictions, min_threshold=0.70)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # SLA < 20 ms
        self.assertLess(elapsed_ms, 20.0)
        self.assertGreater(len(suggestions), 0)
        self.assertIn("Proactive Suggestion", suggestions[0].title)

    async def test_predictive_engine_full_pipeline_and_sla(self):
        engine = PredictiveGoalEngine(min_suggestion_threshold=0.70)

        start = time.perf_counter()
        result = await engine.predict(self.context)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Prediction SLA < 100 ms
        self.assertLess(elapsed_ms, 100.0)
        self.assertTrue(result.success)
        self.assertGreater(len(result.goal_predictions), 0)
        self.assertGreater(len(result.workflow_predictions), 0)

    async def test_empty_context_fallback(self):
        engine = PredictiveGoalEngine()
        empty_context = CognitiveContext()

        result = await engine.predict(empty_context)
        self.assertTrue(result.success)
        self.assertGreater(len(result.goal_predictions), 0)
        self.assertEqual(result.goal_predictions[0].intent_category, "general_assistance")

    async def test_event_publishing(self):
        custom_bus = EventBus()
        events_emitted = []

        def listener(evt):
            events_emitted.append(evt.name)

        custom_bus.subscribe("PredictionGenerated", listener)
        custom_bus.subscribe("WorkflowPredicted", listener)
        custom_bus.subscribe("SuggestionGenerated", listener)
        custom_bus.subscribe("LowConfidencePrediction", listener)

        engine = PredictiveGoalEngine(bus=custom_bus, min_suggestion_threshold=0.60)
        await engine.predict(self.context)
        await asyncio.sleep(0.05)

        self.assertIn("PredictionGenerated", events_emitted)
        self.assertIn("WorkflowPredicted", events_emitted)
        self.assertIn("SuggestionGenerated", events_emitted)


if __name__ == "__main__":
    unittest.main()
