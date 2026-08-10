"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Schema Normalizer.
Normalizes unambiguous values (memory e.g. "8GB" -> "8192 MB", dates, currencies, file sizes)
while strictly preserving the exact original string in StructuredField.value.
Ambiguous values/locales remain un-normalized (normalized_value = None).
"""
import re
import logging
from typing import Optional, Any, Tuple
from intelligence.web.structured.models import StructuredField

logger = logging.getLogger("JARVIS_SchemaNormalizer")


class SchemaNormalizer:
    """
    Normalizes structured field values deterministically without mutating original values.
    """

    def normalize_field(self, field: StructuredField) -> StructuredField:
        if not field.value or not field.value.strip():
            field.normalized_value = None
            return field

        val_str = field.value.strip()

        # 1. RAM / Memory Normalization (e.g. 8GB -> 8192 MB)
        ram_match = re.match(r"^(\d+(\.\d+)?)\s*(GB|MB|KB|TB)$", val_str, re.IGNORECASE)
        if ram_match:
            num = float(ram_match.group(1))
            unit = ram_match.group(3).upper()
            if unit == "GB":
                field.normalized_value = f"{int(num * 1024)} MB"
                field.unit = "MB"
                return field
            elif unit == "TB":
                field.normalized_value = f"{int(num * 1024 * 1024)} MB"
                field.unit = "MB"
                return field
            elif unit == "MB":
                field.normalized_value = f"{int(num)} MB"
                field.unit = "MB"
                return field

        # 2. Percentage Normalization (e.g. 95% -> 0.95)
        pct_match = re.match(r"^(\d+(\.\d+)?)\s*%$", val_str)
        if pct_match:
            field.normalized_value = float(pct_match.group(1)) / 100.0
            field.unit = "RATIO"
            return field

        # 3. Currency Normalization (e.g. $99.99 -> 99.99 USD)
        curr_match = re.match(r"^\$\s*(\d+(\.\d+)?)$", val_str)
        if curr_match:
            field.normalized_value = float(curr_match.group(1))
            field.unit = "USD"
            return field

        # Default: if ambiguous, keep normalized_value as None
        field.normalized_value = None
        return field


schema_normalizer = SchemaNormalizer()
