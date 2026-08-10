"""
Bounded Research Planner for J.A.R.V.I.S. I2.2 V3.
Decomposes target query into max 3 sub-questions + 1 reserved verification query,
enforcing strict execution bounds.
"""

from typing import List
from intelligence.web.research.models import (
    ResearchPlan,
    ResearchQuestion,
    ResearchIntent
)


# HARD EXECUTION BOUNDS
MAX_RESEARCH_ROUNDS = 2
MAX_SEARCH_QUERIES = 4       # 3 plan sub-queries + 1 reserved verification/conflict query
MAX_SOURCES = 5
MAX_PAGES = 4
MAX_EVIDENCE_CHUNKS = 8
MAX_EVIDENCE_CHARS = 12000   # ~3,000 tokens limit for synthesis context
MAX_RESEARCH_TIME_SECONDS = 15.0  # End-to-end global wall-clock deadline


class ResearchPlanner:
    """Generates bounded multi-query research plans."""

    def create_plan(self, query: str, intent: ResearchIntent) -> ResearchPlan:
        """
        Creates a ResearchPlan with max 3 sub-questions.
        Reserves the 4th query capacity for verification/conflict resolution if needed.
        """
        sub_questions: List[ResearchQuestion] = []

        if intent == ResearchIntent.PRODUCT_COMPARISON:
            sub_questions = [
                ResearchQuestion(
                    question_id="sub_q1",
                    query=f"{query} primary official features capabilities",
                    intent=intent,
                    priority=1
                ),
                ResearchQuestion(
                    question_id="sub_q2",
                    query=f"{query} developer pros and cons comparison",
                    intent=intent,
                    priority=2
                )
            ]
        elif intent == ResearchIntent.FACT_CHECK:
            sub_questions = [
                ResearchQuestion(
                    question_id="sub_q1",
                    query=f"{query} official documentation PEP primary source",
                    intent=intent,
                    priority=1
                ),
                ResearchQuestion(
                    question_id="sub_q2",
                    query=f"{query} release notes discussion",
                    intent=intent,
                    priority=2
                )
            ]
        elif intent == ResearchIntent.TECHNICAL_RESEARCH:
            sub_questions = [
                ResearchQuestion(
                    question_id="sub_q1",
                    query=f"{query} official documentation changelog",
                    intent=intent,
                    priority=1
                ),
                ResearchQuestion(
                    question_id="sub_q2",
                    query=f"{query} breaking changes migration guide",
                    intent=intent,
                    priority=2
                )
            ]
        else:
            sub_questions = [
                ResearchQuestion(
                    question_id="sub_q1",
                    query=f"{query} primary documentation overview",
                    intent=intent,
                    priority=1
                ),
                ResearchQuestion(
                    question_id="sub_q2",
                    query=f"{query} latest developments updates",
                    intent=intent,
                    priority=2
                )
            ]

        return ResearchPlan(
            original_query=query,
            primary_intent=intent,
            sub_questions=sub_questions[:3],  # Hard max 3 plan sub-questions
            max_rounds=MAX_RESEARCH_ROUNDS,
            max_sources=MAX_SOURCES
        )

    def create_verification_question(self, topic: str, intent: ResearchIntent) -> ResearchQuestion:
        """Creates the 4th query strictly reserved for verification or conflict resolution."""
        return ResearchQuestion(
            question_id="sub_q_verify",
            query=f"{topic} official primary verification",
            intent=intent,
            priority=1,
            is_verification_query=True
        )


research_planner = ResearchPlanner()
