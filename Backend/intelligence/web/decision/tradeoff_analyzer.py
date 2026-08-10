"""
Trade-off Analysis Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
import uuid
from typing import List
from intelligence.web.decision.models import (
    CandidateEntity,
    Tradeoff,
    TradeoffType,
)


class TradeoffAnalyzer:
    """
    Identifies and preserves explicit trade-offs between candidates.
    Does not force a fake universal winner when genuine trade-offs exist.
    """

    def analyze_tradeoffs(
        self, candidates: List[CandidateEntity]
    ) -> List[Tradeoff]:
        tradeoffs: List[Tradeoff] = []

        if len(candidates) < 2:
            return tradeoffs

        cand_a = candidates[0]
        cand_b = candidates[1]

        price_a = cand_a.attributes.get("price")
        price_b = cand_b.attributes.get("price")

        ram_a = cand_a.attributes.get("ram", 0)
        ram_b = cand_b.attributes.get("ram", 0)

        # Price vs Features / Performance trade-off
        if price_a and price_b and price_a != price_b:
            cheaper, pricier = (cand_a, cand_b) if price_a < price_b else (cand_b, cand_a)
            tradeoffs.append(
                Tradeoff(
                    tradeoff_id=f"to_{uuid.uuid4().hex[:8]}",
                    tradeoff_type=TradeoffType.PRICE_VS_FEATURES,
                    description=f"{cheaper.name} is more affordable, whereas {pricier.name} offers higher specifications at a premium price.",
                    candidate_a_id=cheaper.candidate_id,
                    candidate_b_id=pricier.candidate_id,
                    advantage_a=f"Lower price ({cheaper.attributes.get('price')})",
                    advantage_b=f"Higher specs / features",
                )
            )

        # Performance vs Portability/Battery trade-off
        if ram_a and ram_b and ram_a != ram_b:
            higher_ram, lower_ram = (cand_a, cand_b) if ram_a > ram_b else (cand_b, cand_a)
            tradeoffs.append(
                Tradeoff(
                    tradeoff_id=f"to_{uuid.uuid4().hex[:8]}",
                    tradeoff_type=TradeoffType.PERFORMANCE_VS_BATTERY,
                    description=f"{higher_ram.name} provides superior memory headroom ({higher_ram.attributes.get('ram')}GB), while {lower_ram.name} offers efficiency.",
                    candidate_a_id=higher_ram.candidate_id,
                    candidate_b_id=lower_ram.candidate_id,
                    advantage_a=f"Higher RAM ({higher_ram.attributes.get('ram')}GB)",
                    advantage_b="Potentially lower power consumption / battery efficiency",
                )
            )

        return tradeoffs


tradeoff_analyzer = TradeoffAnalyzer()
