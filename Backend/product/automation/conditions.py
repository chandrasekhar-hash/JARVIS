"""
JARVIS Product 1.7 - Condition Evaluator.
Evaluates pre-execution conditions (file_exists, knowledge_indexed, memory_contains, battery_level_above, document_tagged).
"""

import os
import logging
from typing import Dict, Any
from .interfaces import IConditionEvaluator
from .models import ConditionConfig

logger = logging.getLogger(__name__)


class ConditionEvaluator(IConditionEvaluator):
    def evaluate(self, condition: ConditionConfig, context: Dict[str, Any]) -> bool:
        ctype = condition.condition_type.lower()

        if ctype == "file_exists":
            target_path = context.get("file_path", condition.target)
            return os.path.exists(target_path)

        elif ctype == "knowledge_indexed":
            # Evaluates if target document ID is present in context or metadata
            return context.get("document_status") == "INDEXED" or condition.expected_value is True

        elif ctype == "memory_contains":
            # Evaluates memory fact presence
            memory_fact = context.get("memory_fact", "")
            return condition.target.lower() in memory_fact.lower()

        elif ctype == "battery_level_above":
            current_battery = context.get("battery_pct", 100)
            return current_battery >= float(condition.expected_value)

        elif ctype == "document_tagged":
            doc_tags = context.get("doc_tags", [])
            return condition.expected_value in doc_tags

        # Default fallback: equality check
        actual = context.get(condition.target)
        return str(actual) == str(condition.expected_value)
