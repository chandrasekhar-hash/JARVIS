"""
Intent Classification Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
import re
from intelligence.web.decision.models import DecisionIntent


class DecisionIntentClassifier:
    """
    Classifies user queries into decision intents or signals fast bypass for conversational/factual queries.
    """

    COMPARISON_PATTERNS = [
        r"\bcompare\b", r"\bversus\b", r"\bvs\.?\b", r"\bdifference between\b", r"\bwhich is better\b"
    ]

    PURCHASE_PATTERNS = [
        r"\bbuy\b", r"\bunder ₹?\d+\b", r"\bprice under\b", r"\bbudget\b", r"\blaptop for\b", r"\bphone for\b", r"\bcheapest\b", r"\bcheap\b"
    ]

    TECH_PATTERNS = [
        r"\bframework for\b", r"\btechnology stack\b", r"\blibrary for\b", r"\bdatabase for\b", r"\breact or vue\b"
    ]

    RECOMMENDATION_PATTERNS = [
        r"\brecommend\b", r"\bwhat should i (choose|buy|use|get)\b", r"\bbest option\b", r"\bbest choice\b"
    ]

    RANKING_PATTERNS = [
        r"\brank\b", r"\btop \d+\b", r"\bbest \d+\b"
    ]

    TRADEOFF_PATTERNS = [
        r"\btrade-off\b", r"\btradeoff\b", r"\bpros and cons\b", r"\badvantages and disadvantages\b"
    ]

    BEST_USE_CASE_PATTERNS = [
        r"\bbest (laptop|phone|camera|tool|framework|language) for\b"
    ]

    ALTERNATIVE_PATTERNS = [
        r"\balternative\b", r"\balternatives to\b", r"\breplacement for\b"
    ]

    CONVERSATIONAL_PATTERNS = [
        r"^(hello|hi|hey|what is|who is|explain|define|how does|what does)\b"
    ]

    def classify_intent(self, query: str) -> DecisionIntent:
        if not query or not query.strip():
            return DecisionIntent.NO_DECISION_REQUIRED

        q_lower = query.lower().strip()

        # Check conversational bypass
        for pat in self.CONVERSATIONAL_PATTERNS:
            if re.search(pat, q_lower) and not any(k in q_lower for k in ["best", "compare", "vs", "recommend", "choose", "buy", "under"]):
                return DecisionIntent.NO_DECISION_REQUIRED

        if any(re.search(pat, q_lower) for pat in self.TRADEOFF_PATTERNS):
            return DecisionIntent.TRADEOFF_ANALYSIS

        if any(re.search(pat, q_lower) for pat in self.COMPARISON_PATTERNS):
            return DecisionIntent.COMPARISON

        if any(re.search(pat, q_lower) for pat in self.PURCHASE_PATTERNS):
            return DecisionIntent.PURCHASE_DECISION

        if any(re.search(pat, q_lower) for pat in self.TECH_PATTERNS):
            return DecisionIntent.TECHNOLOGY_SELECTION

        if any(re.search(pat, q_lower) for pat in self.BEST_USE_CASE_PATTERNS):
            return DecisionIntent.BEST_FOR_USE_CASE

        if any(re.search(pat, q_lower) for pat in self.RECOMMENDATION_PATTERNS):
            return DecisionIntent.RECOMMENDATION

        if any(re.search(pat, q_lower) for pat in self.RANKING_PATTERNS):
            return DecisionIntent.OPTION_RANKING

        if any(re.search(pat, q_lower) for pat in self.ALTERNATIVE_PATTERNS):
            return DecisionIntent.ALTERNATIVE_SELECTION

        if "under" in q_lower or "at least" in q_lower or "minimum" in q_lower:
            return DecisionIntent.CONSTRAINT_FILTERING

        return DecisionIntent.NO_DECISION_REQUIRED


intent_classifier = DecisionIntentClassifier()
