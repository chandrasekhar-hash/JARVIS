import time
from typing import List, Dict, Any, Optional
from collections import Counter
from user_model.models import (
    UserHabitProfile,
    UserHabit,
    ActivityWindow,
    WorkflowAffinity,
    PreferenceObservation,
    UserConsent,
)
from tools.telemetry import log_structured, backend_log


class HabitAnalyzer:
    """
    Extracts working patterns, tool usage frequencies, daily activity windows,
    and workflow affinities from observation logs and interaction telemetry.
    """

    def __init__(self, min_frequency_threshold: int = 2):
        self.min_frequency_threshold = min_frequency_threshold

    def analyze_habits(
        self,
        user_id: str,
        observations: List[PreferenceObservation],
        tool_usages: List[Dict[str, Any]],
        consent: Optional[UserConsent] = None,
    ) -> UserHabitProfile:
        try:
            if consent and (not consent.opt_in_personalization or not consent.allow_habit_analysis):
                log_structured(backend_log, "INFO", f"[HabitAnalyzer] Habit analysis skipped due to consent settings for user '{user_id}'")
                return UserHabitProfile(user_id=user_id, last_analyzed_at=time.time())

            habits: List[UserHabit] = []
            activity_windows: List[ActivityWindow] = []
            workflow_affinities: List[WorkflowAffinity] = []
            tool_counter: Counter = Counter()

            # 1. Analyze tool usage frequency & top tools
            for usage in tool_usages:
                tool_name = usage.get("tool_name") or usage.get("app_name")
                if tool_name:
                    count = usage.get("count", 1)
                    tool_counter[str(tool_name)] += count

            for tool_name, count in tool_counter.items():
                if count >= self.min_frequency_threshold:
                    habits.append(
                        UserHabit(
                            habit_name=f"frequent_tool_{tool_name}",
                            category="tool_affinity",
                            frequency_count=count,
                            confidence=min(1.0, round(0.4 + (count * 0.1), 2)),
                            associated_tools=[tool_name],
                            last_observed_at=time.time(),
                        )
                    )

            top_tools = [tool for tool, _ in tool_counter.most_common(10)]

            # 2. Extract workflow affinities from observation sequences
            workflow_sequences: Dict[str, int] = {}
            for obs in observations:
                if obs.category == "workflow":
                    wf_pattern = str(obs.observed_value)
                    workflow_sequences[wf_pattern] = workflow_sequences.get(wf_pattern, 0) + 1

            for wf_pattern, usage_cnt in workflow_sequences.items():
                workflow_affinities.append(
                    WorkflowAffinity(
                        workflow_pattern=wf_pattern,
                        affinity_score=min(1.0, round(0.5 + (usage_cnt * 0.1), 2)),
                        usage_count=usage_cnt,
                        preferred_tool_chain=top_tools[:3],
                    )
                )

            # 3. Determine active daily time windows (hours 0-23, day 0-6)
            hour_counts: Counter = Counter()
            for obs in observations:
                if obs.timestamp > 0:
                    # Convert timestamp to local hour
                    local_struct = time.localtime(obs.timestamp)
                    hour_counts[(local_struct.tm_wday, local_struct.tm_hour)] += 1

            for (wday, hour), cnt in hour_counts.most_common(5):
                activity_windows.append(
                    ActivityWindow(
                        day_of_week=wday,
                        start_hour=hour,
                        end_hour=(hour + 1) % 24,
                        activity_level=min(1.0, round(cnt / 10.0, 2)),
                    )
                )

            profile = UserHabitProfile(
                user_id=user_id,
                habits=habits,
                activity_windows=activity_windows,
                workflow_affinities=workflow_affinities,
                top_tools=top_tools,
                last_analyzed_at=time.time(),
            )

            log_structured(
                backend_log,
                "INFO",
                f"[HabitAnalyzer] Analyzed {len(habits)} habits and {len(top_tools)} top tools for user '{user_id}'",
            )
            return profile

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[HabitAnalyzer] Error analyzing habits: {str(e)}")
            return UserHabitProfile(user_id=user_id, last_analyzed_at=time.time())
