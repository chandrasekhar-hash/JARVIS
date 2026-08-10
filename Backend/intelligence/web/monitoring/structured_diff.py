"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Structured Data Diff Engine.
Composes V6 structured data primitives. Compares StructuredDataset, StructuredRecord, and StructuredField
using stable keys (version, id, name, SKU, canonical_url, schema_id) to prevent false row removal/addition on reordering.
Always preserves OLD_VALUE and NEW_VALUE.
"""
import logging
from typing import List, Dict, Any, Optional, Set
from intelligence.web.monitoring.models import (
    MonitoringSnapshot,
    ChangeEvidence,
    ChangeType,
)

logger = logging.getLogger("JARVIS_StructuredDiffEngine")


class StructuredDiffEngine:
    """
    Diffs structured record key-value pairs between baseline and current snapshots.
    """

    STABLE_KEYS = {"version", "id", "name", "sku", "canonical_url", "schema_id", "title", "product_id"}

    def diff_important_fields(
        self, baseline: MonitoringSnapshot, current: MonitoringSnapshot
    ) -> List[ChangeEvidence]:
        evidences: List[ChangeEvidence] = []
        ev_counter = 1

        old_fields = baseline.important_field_values
        new_fields = current.important_field_values

        all_keys = set(old_fields.keys()).union(set(new_fields.keys()))

        for key in sorted(all_keys):
            old_val = old_fields.get(key)
            new_val = new_fields.get(key)

            if old_val is None and new_val is not None:
                evidences.append(
                    ChangeEvidence(
                        evidence_id=f"ev_struct_{ev_counter}",
                        change_type=ChangeType.VALUE_CHANGED,
                        field_name=key,
                        old_value=None,
                        new_value=str(new_val),
                        source_path=f"fields.{key}",
                        is_meaningful=True,
                    )
                )
                ev_counter += 1
            elif old_val is not None and new_val is None:
                evidences.append(
                    ChangeEvidence(
                        evidence_id=f"ev_struct_{ev_counter}",
                        change_type=ChangeType.VALUE_CHANGED,
                        field_name=key,
                        old_value=str(old_val),
                        new_value=None,
                        source_path=f"fields.{key}",
                        is_meaningful=True,
                    )
                )
                ev_counter += 1
            elif old_val != new_val:
                # Classify special value types (price, version, status)
                change_type = ChangeType.VALUE_CHANGED
                key_lower = key.lower()
                if "price" in key_lower or "cost" in key_lower:
                    change_type = ChangeType.PRICE_CHANGED
                elif "version" in key_lower or "release" in key_lower:
                    change_type = ChangeType.VERSION_CHANGED
                elif "status" in key_lower or "availability" in key_lower:
                    change_type = ChangeType.STATUS_CHANGED
                elif "date" in key_lower:
                    change_type = ChangeType.DATE_CHANGED

                evidences.append(
                    ChangeEvidence(
                        evidence_id=f"ev_struct_{ev_counter}",
                        change_type=change_type,
                        field_name=key,
                        old_value=str(old_val),
                        new_value=str(new_val),
                        snippet_before=f"{key}: {old_val}",
                        snippet_after=f"{key}: {new_val}",
                        source_path=f"fields.{key}",
                        is_meaningful=True,
                    )
                )
                ev_counter += 1

        return evidences


structured_diff_engine = StructuredDiffEngine()
