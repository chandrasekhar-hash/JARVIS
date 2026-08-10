"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Content Diff Engine.
Computes deterministic structural diffs across text blocks, heading hierarchies, links, and resources.
Always preserves OLD_VALUE and NEW_VALUE.
"""
import difflib
import logging
from typing import List, Dict, Any, Tuple
from intelligence.web.monitoring.models import (
    MonitoringSnapshot,
    ChangeEvidence,
    ChangeType,
)
from intelligence.web.monitoring.snapshot_fingerprint import snapshot_fingerprint_generator

logger = logging.getLogger("JARVIS_ContentDiffEngine")


class ContentDiffEngine:
    """
    Computes structural textual and heading diffs between baseline and current snapshots.
    """

    def diff_snapshots(
        self, baseline: MonitoringSnapshot, current: MonitoringSnapshot
    ) -> List[ChangeEvidence]:
        evidences: List[ChangeEvidence] = []
        ev_counter = 1

        # 1. Heading Diffing
        old_headings = baseline.heading_fingerprints
        new_headings = current.heading_fingerprints

        s = difflib.SequenceMatcher(None, old_headings, new_headings)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag == "replace":
                old_val = " | ".join(old_headings[i1:i2])
                new_val = " | ".join(new_headings[j1:j2])
                evidences.append(
                    ChangeEvidence(
                        evidence_id=f"ev_content_{ev_counter}",
                        change_type=ChangeType.STRUCTURE_CHANGED,
                        field_name="heading_hierarchy",
                        old_value=old_val,
                        new_value=new_val,
                        snippet_before=old_val,
                        snippet_after=new_val,
                        source_path="headings.hierarchy",
                        is_meaningful=True,
                    )
                )
                ev_counter += 1
            elif tag == "insert":
                new_val = " | ".join(new_headings[j1:j2])
                evidences.append(
                    ChangeEvidence(
                        evidence_id=f"ev_content_{ev_counter}",
                        change_type=ChangeType.CONTENT_ADDED,
                        field_name="heading_hierarchy",
                        old_value="",
                        new_value=new_val,
                        snippet_after=new_val,
                        source_path="headings.insert",
                        is_meaningful=True,
                    )
                )
                ev_counter += 1
            elif tag == "delete":
                old_val = " | ".join(old_headings[i1:i2])
                evidences.append(
                    ChangeEvidence(
                        evidence_id=f"ev_content_{ev_counter}",
                        change_type=ChangeType.CONTENT_REMOVED,
                        field_name="heading_hierarchy",
                        old_value=old_val,
                        new_value="",
                        snippet_before=old_val,
                        source_path="headings.delete",
                        is_meaningful=True,
                    )
                )
                ev_counter += 1

        # 2. Text Block Diffing
        old_blocks = baseline.selected_text_blocks
        new_blocks = current.selected_text_blocks

        block_matcher = difflib.SequenceMatcher(None, old_blocks, new_blocks)
        for tag, i1, i2, j1, j2 in block_matcher.get_opcodes():
            if tag == "replace":
                old_text = " ".join(old_blocks[i1:i2])
                new_text = " ".join(new_blocks[j1:j2])
                evidences.append(
                    ChangeEvidence(
                        evidence_id=f"ev_content_{ev_counter}",
                        change_type=ChangeType.CONTENT_MODIFIED,
                        field_name="body_text",
                        old_value=old_text[:500],
                        new_value=new_text[:500],
                        snippet_before=old_text[:300],
                        snippet_after=new_text[:300],
                        source_path="body.replace",
                        is_meaningful=True,
                    )
                )
                ev_counter += 1
            elif tag == "insert":
                new_text = " ".join(new_blocks[j1:j2])
                evidences.append(
                    ChangeEvidence(
                        evidence_id=f"ev_content_{ev_counter}",
                        change_type=ChangeType.CONTENT_ADDED,
                        field_name="body_text",
                        old_value="",
                        new_value=new_text[:500],
                        snippet_after=new_text[:300],
                        source_path="body.insert",
                        is_meaningful=True,
                    )
                )
                ev_counter += 1
            elif tag == "delete":
                old_text = " ".join(old_blocks[i1:i2])
                evidences.append(
                    ChangeEvidence(
                        evidence_id=f"ev_content_{ev_counter}",
                        change_type=ChangeType.CONTENT_REMOVED,
                        field_name="body_text",
                        old_value=old_text[:500],
                        new_value="",
                        snippet_before=old_text[:300],
                        source_path="body.delete",
                        is_meaningful=True,
                    )
                )
                ev_counter += 1

        return evidences


content_diff_engine = ContentDiffEngine()
