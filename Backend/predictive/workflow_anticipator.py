from typing import List
from unified_context.models import CognitiveContext
from predictive.models import IntentPrediction, WorkflowPrediction
from tools.telemetry import log_structured, backend_log


class WorkflowAnticipator:
    """
    Predicts multi-step tool sequences, action paths, and completion probabilities
    from forecasted intent and cognitive context.
    """

    def __init__(self):
        pass

    def anticipate_workflows(
        self, intents: List[IntentPrediction], context: CognitiveContext
    ) -> List[WorkflowPrediction]:
        workflows: List[WorkflowPrediction] = []
        try:
            for intent in intents[:2]:  # Focus on top 2 intent categories
                if intent.intent_category == "code_development":
                    workflows.append(
                        WorkflowPrediction(
                            predicted_tool_sequence=["view_file", "run_command", "git"],
                            predicted_actions=[
                                "Inspect modified source code files",
                                "Run build and test verification suite",
                                "Commit validated changes to repository",
                            ],
                            completion_probability=round(min(0.95, intent.probability + 0.10), 2),
                        )
                    )
                elif intent.intent_category == "web_research":
                    workflows.append(
                        WorkflowPrediction(
                            predicted_tool_sequence=["search_web", "read_url_content", "write_to_file"],
                            predicted_actions=[
                                "Perform web search for query topics",
                                "Fetch and summarize documentation content",
                                "Persist research summary to project notes",
                            ],
                            completion_probability=round(min(0.90, intent.probability + 0.05), 2),
                        )
                    )
                elif intent.intent_category == "document_editing":
                    workflows.append(
                        WorkflowPrediction(
                            predicted_tool_sequence=["view_file", "replace_file_content"],
                            predicted_actions=[
                                "Open target document file",
                                "Apply requested edits and updates",
                            ],
                            completion_probability=round(min(0.85, intent.probability), 2),
                        )
                    )

            log_structured(
                backend_log,
                "INFO",
                f"[WorkflowAnticipator] Anticipated {len(workflows)} multi-step workflows",
            )
            return workflows

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[WorkflowAnticipator] Error anticipating workflows: {str(e)}")
            return workflows
