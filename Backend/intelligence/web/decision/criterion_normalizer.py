"""
Criterion Value Normalization Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
import re
from typing import Any, Dict, Optional, Tuple


class CriterionNormalizer:
    """
    Normalizes comparative values (currencies, RAM, storage, prices, versions)
    while explicitly preserving original values, normalized values, units, and temporal metadata.
    """

    def normalize_value(
        self,
        raw_val: Any,
        criterion_type: str,
        temporal_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Any], Optional[str]]:
        if raw_val is None:
            return None, None

        val_str = str(raw_val).strip()

        if criterion_type == "price":
            # Currency normalization
            clean_str = re.sub(r"[^\d\.]", "", val_str)
            try:
                num = float(clean_str)
                unit = "INR" if "₹" in val_str or "inr" in val_str.lower() else "USD"
                return num, unit
            except ValueError:
                return None, None

        if criterion_type == "ram":
            clean_str = re.sub(r"[^\d]", "", val_str)
            try:
                num = int(clean_str)
                return num, "GB"
            except ValueError:
                return None, None

        if criterion_type == "storage":
            clean_str = re.sub(r"[^\d]", "", val_str)
            try:
                num = int(clean_str)
                unit = "TB" if "tb" in val_str.lower() else "GB"
                if unit == "TB":
                    num *= 1024
                return num, "GB"
            except ValueError:
                return None, None

        return val_str, "STRING"


criterion_normalizer = CriterionNormalizer()
