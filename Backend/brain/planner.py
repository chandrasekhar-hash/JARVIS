import re
from typing import List, Optional
from brain.models import ActionStep, ActionPlan
from brain.conversation import reference_resolver
from tools.classifier import classify_intent
from tools.telemetry import log_structured, backend_log

class ToolPlanner:
    def parse_intent_to_plan(
        self,
        query: str,
        context_summary: Optional[str] = None
    ) -> ActionPlan:
        """Parses natural language intent and constructs a structured ActionPlan."""
        resolved_query = reference_resolver.resolve_references(query)
        log_structured(backend_log, "INFO", f"[Planner] Analyzing query: '{resolved_query}'")

        steps: List[ActionStep] = []

        # 1. Visual Target Grounding for Click Requests (e.g. "Click the Retry button")
        query_lower = resolved_query.lower()
        if "click" in query_lower or "press" in query_lower:
            target_match = re.search(r'(?:click|press)\s+(?:the\s+)?(.+)', query_lower)
            if target_match:
                target_name = target_match.group(1).strip()
                try:
                    from vision import vision_orchestrator, element_grounding_engine
                    pipeline_out = vision_orchestrator.run_snapshot()
                    if pipeline_out:
                        _, _, ui_obs, _ = pipeline_out
                        grounded = element_grounding_engine.ground_target(target_name, ui_obs)
                        if grounded:
                            steps.append(
                                ActionStep(
                                    step_id=1,
                                    tool_name="window_control",
                                    arguments={
                                        "action": "focus",
                                        "handle": 0
                                    },
                                    description=f"Visual Grounding: Click '{grounded.label}' ({grounded.element_type.value}) at ({grounded.bbox.center_x}, {grounded.bbox.center_y})"
                                )
                            )
                            return ActionPlan(intent=resolved_query, steps=steps, execution_mode="immediate")
                except Exception as e_ground:
                    log_structured(backend_log, "WARNING", f"[Planner] Visual grounding omitted: {str(e_ground)}")

        # 2. Multi-step chaining decomposition using conjunctions ('and then', 'and', 'then', ';')
        sub_intents = [s.strip() for s in re.split(r'\b(?:and then|and|then)\b|;', resolved_query, flags=re.IGNORECASE) if s.strip()]

        for idx, sub in enumerate(sub_intents, 1):
            direct_match = classify_intent(sub)
            if direct_match:
                t_name = direct_match["tool_name"]
                t_args = direct_match["arguments"]
                steps.append(
                    ActionStep(
                        step_id=idx,
                        tool_name=t_name,
                        arguments=t_args,
                        description=f"Execute {t_name} with {t_args}"
                    )
                )

        if steps:
            exec_mode = "background" if any(s.tool_name in ["fs_search_files", "browser_read_page"] for s in steps) else "immediate"
            return ActionPlan(
                intent=resolved_query,
                steps=steps,
                execution_mode=exec_mode
            )

        # 3. Heuristic fallback decomposition for common multi-step phrases
        if "open chrome" in query_lower and "search" in query_lower:
            search_match = re.search(r'search\s+(for\s+)?(.+)', query_lower)
            q = search_match.group(2).strip() if search_match else "Google"
            steps.append(ActionStep(step_id=1, tool_name="browser_open_url", arguments={"urls": ["https://www.google.com"]}, description="Open browser"))
            steps.append(ActionStep(step_id=2, tool_name="browser_search", arguments={"query": q}, description=f"Search browser for '{q}'"))
            return ActionPlan(intent=resolved_query, steps=steps, execution_mode="immediate")

        if "open" in query_lower and "folder" in query_lower:
            folder_match = re.search(r'open\s+(the\s+)?(\w+)\s+folder', query_lower)
            folder_name = folder_match.group(2).strip() if folder_match else "Downloads"
            steps.append(ActionStep(step_id=1, tool_name="fs_open_folder", arguments={"folder_path": folder_name}, description=f"Open {folder_name} folder"))
            return ActionPlan(intent=resolved_query, steps=steps, execution_mode="immediate")

        # Fallback single step placeholder if no patterns match
        steps.append(
            ActionStep(
                step_id=1,
                tool_name="agent_reasoning",
                arguments={"query": resolved_query},
                description="Process general conversation and intent"
            )
        )

        return ActionPlan(
            intent=resolved_query,
            steps=steps,
            execution_mode="immediate"
        )

tool_planner = ToolPlanner()
