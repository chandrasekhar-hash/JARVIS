"""
Query Planner for J.A.R.V.I.S. I2.2 V1 Web Search Foundation.
Generates 1-3 targeted search queries with strict bounds (max 3) and no recursive expansion loops.
"""
import re
from typing import List
from intelligence.web.models import WebSearchIntent

MAX_PLANNED_QUERIES = 3


class WebQueryPlanner:
    """
    Query planner generating clean, targeted search queries based on user intent.
    Enforces a strict upper bound of MAX_PLANNED_QUERIES (3) to avoid query inflation.
    """

    def __init__(self):
        self._conversational_fillers = [
            r"^\s*(jarvis|hey jarvis|please|can you|could you|kindly|search for|look up|find me|find|tell me|get me)\s+",
            r"\s*(for me|please|thanks|thank you)\s*$",
        ]

    def clean_user_query(self, query: str) -> str:
        """Strips conversational fluff and leading/trailing whitespace."""
        q = query.strip()
        prev = ""
        while q != prev:
            prev = q
            for filler in self._conversational_fillers:
                q = re.sub(filler, "", q, flags=re.IGNORECASE).strip()
        return q or query.strip()

    def plan_queries(self, user_query: str, intent: WebSearchIntent) -> List[str]:
        """
        Generates 1 to 3 distinct search queries based on intent.
        
        Examples:
        - User: "Latest Gemini API updates"
          Intent: CURRENT_INFORMATION
          Planned: ["Gemini API latest updates", "Gemini API release notes"]
          
        - User: "FastAPI authentication docs"
          Intent: DOCUMENTATION
          Planned: ["FastAPI authentication official documentation", "FastAPI authentication docs"]
        """
        base_query = self.clean_user_query(user_query)
        if not base_query:
            return [user_query]

        planned: List[str] = [base_query]

        if intent == WebSearchIntent.DOCUMENTATION:
            if "doc" not in base_query.lower():
                planned.append(f"{base_query} official documentation")
            else:
                planned.append(f"{base_query} guide")
        elif intent == WebSearchIntent.OFFICIAL_SOURCE:
            if "official" not in base_query.lower():
                planned.append(f"{base_query} official website")
        elif intent in (WebSearchIntent.CURRENT_INFORMATION, WebSearchIntent.NEWS):
            if not any(w in base_query.lower() for w in ["latest", "recent", "release notes", "changelog"]):
                planned.append(f"{base_query} latest updates")
                planned.append(f"{base_query} release notes")
            else:
                planned.append(f"{base_query} changelog")
        elif intent == WebSearchIntent.TECHNICAL:
            if "solution" not in base_query.lower() and "fix" not in base_query.lower():
                planned.append(f"{base_query} fix solution")
        elif intent == WebSearchIntent.ACADEMIC:
            if "paper" not in base_query.lower():
                planned.append(f"{base_query} research paper")

        # Deduplicate while preserving order
        unique_queries = []
        seen = set()
        for q in planned:
            q_norm = q.strip().lower()
            if q_norm not in seen:
                seen.add(q_norm)
                unique_queries.append(q.strip())

        # Enforce strict maximum query bound (max 3)
        return unique_queries[:MAX_PLANNED_QUERIES]


# Global singleton instance
query_planner = WebQueryPlanner()
