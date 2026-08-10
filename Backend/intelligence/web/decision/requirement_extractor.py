"""
Requirement Extraction & Conflict Detection Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
import re
import uuid
from typing import List, Tuple, Optional
from intelligence.web.decision.models import (
    ConstraintType,
    DecisionConflict,
    DecisionConflictStatus,
    DecisionRequirement,
    RequirementType,
)


class RequirementExtractor:
    """
    Extracts explicit user requirements, distinguishing hard constraints from soft preferences,
    and detects user preference conflicts.
    """

    BUDGET_RE = re.compile(r"\b(?:under|below|less than|budget of|max|maximum)\s*(?:₹|\$|eur|usd|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(k|lakh|thousand)?\b", re.IGNORECASE)
    RAM_RE = re.compile(r"\b(?:at least|min|minimum)?\s*(\d+)\s*gb\s*(?:ram|memory)?\b", re.IGNORECASE)
    STORAGE_RE = re.compile(r"\b(?:at least|min|minimum)?\s*(\d+)\s*(gb|tb)\s*(?:ssd|storage)?\b", re.IGNORECASE)

    def extract_requirements(
        self, query: str
    ) -> Tuple[List[DecisionRequirement], List[DecisionConflict]]:
        requirements: List[DecisionRequirement] = []
        conflicts: List[DecisionConflict] = []
        q_lower = query.lower()

        # 1. Check Budget / Price Max (HARD_CONSTRAINT)
        budget_match = self.BUDGET_RE.search(query)
        if budget_match:
            val_str = budget_match.group(1).replace(",", "")
            mult = budget_match.group(2)
            num_val = float(val_str)
            if mult:
                m_lower = mult.lower()
                if m_lower == "k" or m_lower == "thousand":
                    num_val *= 1000
                elif m_lower == "lakh":
                    num_val *= 100000

            requirements.append(
                DecisionRequirement(
                    requirement_id=f"req_{uuid.uuid4().hex[:8]}",
                    text=f"Budget under {num_val}",
                    requirement_type=RequirementType.HARD_CONSTRAINT,
                    constraint_type=ConstraintType.BUDGET_MAX,
                    target_value=num_val,
                    unit="INR" if "₹" in query else "USD",
                    original_wording=budget_match.group(0),
                )
            )

        # 2. Check RAM Min (HARD_CONSTRAINT if "must" or "at least")
        ram_match = self.RAM_RE.search(query)
        if ram_match:
            ram_val = int(ram_match.group(1))
            is_must = "must" in q_lower or "at least" in q_lower or "minimum" in q_lower
            req_type = RequirementType.HARD_CONSTRAINT if is_must else RequirementType.SOFT_PREFERENCE
            requirements.append(
                DecisionRequirement(
                    requirement_id=f"req_{uuid.uuid4().hex[:8]}",
                    text=f"RAM at least {ram_val} GB",
                    requirement_type=req_type,
                    constraint_type=ConstraintType.RAM_MIN,
                    target_value=ram_val,
                    unit="GB",
                    original_wording=ram_match.group(0),
                )
            )

        # 3. Check Storage Min
        storage_match = self.STORAGE_RE.search(query)
        if storage_match:
            st_val = int(storage_match.group(1))
            st_unit = storage_match.group(2).upper()
            requirements.append(
                DecisionRequirement(
                    requirement_id=f"req_{uuid.uuid4().hex[:8]}",
                    text=f"Storage at least {st_val} {st_unit}",
                    requirement_type=RequirementType.SOFT_PREFERENCE,
                    constraint_type=ConstraintType.STORAGE_MIN,
                    target_value=st_val,
                    unit=st_unit,
                    original_wording=storage_match.group(0),
                )
            )

        # 4. Soft preferences (battery, camera, performance, lightweight)
        if "battery" in q_lower:
            requirements.append(
                DecisionRequirement(
                    requirement_id=f"req_{uuid.uuid4().hex[:8]}",
                    text="Good battery life",
                    requirement_type=RequirementType.SOFT_PREFERENCE,
                    constraint_type=ConstraintType.FEATURE_REQUIRED,
                    target_value="battery",
                    original_wording="battery",
                )
            )
        if "camera" in q_lower:
            requirements.append(
                DecisionRequirement(
                    requirement_id=f"req_{uuid.uuid4().hex[:8]}",
                    text="Great camera quality",
                    requirement_type=RequirementType.SOFT_PREFERENCE,
                    constraint_type=ConstraintType.FEATURE_REQUIRED,
                    target_value="camera",
                    original_wording="camera",
                )
            )
        if "coding" in q_lower or "programming" in q_lower or "developer" in q_lower:
            requirements.append(
                DecisionRequirement(
                    requirement_id=f"req_{uuid.uuid4().hex[:8]}",
                    text="Optimized for coding & development",
                    requirement_type=RequirementType.SOFT_PREFERENCE,
                    constraint_type=ConstraintType.FEATURE_REQUIRED,
                    target_value="coding",
                    original_wording="coding",
                )
            )

        # 5. Detect User Preference Conflicts (e.g., cheapest + performance/best)
        if ("cheapest" in q_lower or "cheap" in q_lower or "budget" in q_lower) and ("performance" in q_lower or "fastest" in q_lower or "best" in q_lower):
            conflicts.append(
                DecisionConflict(
                    conflict_id=f"conf_{uuid.uuid4().hex[:8]}",
                    conflict_type=DecisionConflictStatus.REQUIREMENT_CONFLICT,
                    description="User requested both lowest price/budget and maximum performance, presenting an inherent cost-to-performance trade-off.",
                    conflicting_requirements=["cheapest", "performance"],
                    suggested_resolution="Highlight best value-for-money options balancing price and performance.",
                )
            )

        return requirements, conflicts


requirement_extractor = RequirementExtractor()
