import re
from typing import List, Dict, Any
from unified_context.models import CognitiveContext
from predictive.models import IntentPrediction, PredictionCandidate
from tools.telemetry import log_structured, backend_log


class IntentForecaster:
    """
    Analyzes unified cognitive context to classify user intent probabilities
    and generate goal prediction candidates.
    Does NOT query database or external components directly.
    """

    def __init__(self):
        self.intent_keywords = {
            "code_development": ["vscode", "python", "git", "build", "editor", "script", "repo"],
            "web_research": ["browser", "chrome", "search", "http", "query", "url", "scrape"],
            "document_editing": ["document", "pdf", "file", "word", "text", "notes"],
            "system_maintenance": ["system", "terminal", "powershell", "clean", "logs"],
        }

    def forecast_intents(self, context: CognitiveContext) -> List[IntentPrediction]:
        predictions: List[IntentPrediction] = []
        try:
            if not context or not context.chunks:
                # Fallback on empty context
                return [
                    IntentPrediction(
                        intent_category="general_assistance",
                        probability=0.50,
                        matched_signals=["fallback_default"],
                    )
                ]

            full_text = context.formatted_prompt_context.lower()
            intent_scores: Dict[str, float] = {}
            matched_signals_map: Dict[str, List[str]] = {}

            for intent, keywords in self.intent_keywords.items():
                matches = [kw for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", full_text)]
                if matches:
                    score = min(1.0, round(0.40 + len(matches) * 0.15, 2))
                    intent_scores[intent] = score
                    matched_signals_map[intent] = matches

            for intent, prob in intent_scores.items():
                predictions.append(
                    IntentPrediction(
                        intent_category=intent,
                        probability=prob,
                        matched_signals=matched_signals_map.get(intent, []),
                    )
                )

            if not predictions:
                predictions.append(
                    IntentPrediction(
                        intent_category="general_assistance",
                        probability=0.50,
                        matched_signals=["fallback_no_matches"],
                    )
                )

            predictions.sort(key=lambda p: p.probability, reverse=True)
            log_structured(
                backend_log,
                "INFO",
                f"[IntentForecaster] Classified {len(predictions)} intents (Top: {predictions[0].intent_category})",
            )
            return predictions

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[IntentForecaster] Error forecasting intent: {str(e)}")
            return [
                IntentPrediction(
                    intent_category="general_assistance",
                    probability=0.50,
                    matched_signals=["fallback_error"],
                )
            ]

    def generate_candidates(
        self, intents: List[IntentPrediction], context: CognitiveContext
    ) -> List[PredictionCandidate]:
        candidates: List[PredictionCandidate] = []

        for intent in intents:
            if intent.intent_category == "code_development":
                candidates.append(
                    PredictionCandidate(
                        goal_description="Run automated tests and commit code changes",
                        intent_category=intent.intent_category,
                        raw_score=intent.probability,
                        signals=intent.matched_signals,
                    )
                )
            elif intent.intent_category == "web_research":
                candidates.append(
                    PredictionCandidate(
                        goal_description="Summarize documentation and save research notes",
                        intent_category=intent.intent_category,
                        raw_score=intent.probability,
                        signals=intent.matched_signals,
                    )
                )
            elif intent.intent_category == "document_editing":
                candidates.append(
                    PredictionCandidate(
                        goal_description="Review and format technical documentation",
                        intent_category=intent.intent_category,
                        raw_score=intent.probability,
                        signals=intent.matched_signals,
                    )
                )
            else:
                candidates.append(
                    PredictionCandidate(
                        goal_description="Provide proactive assistance for active task",
                        intent_category=intent.intent_category,
                        raw_score=intent.probability,
                        signals=intent.matched_signals,
                    )
                )

        return candidates
