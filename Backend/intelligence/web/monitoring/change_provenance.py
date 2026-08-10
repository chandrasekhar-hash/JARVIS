"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Change Provenance Engine.
Validates fail-closed change provenance and snapshot lineage (N-1 -> N).
Unverified evidence drops unproven findings before final classification.
"""
import logging
from typing import List, Dict, Any
from intelligence.web.monitoring.models import ChangeFinding, MonitoringSnapshot

logger = logging.getLogger("JARVIS_ChangeProvenance")


class ChangeProvenanceEngine:
    """
    Validates provenance completeness for change findings.
    """

    def validate_finding_provenance(
        self, finding: ChangeFinding, baseline: MonitoringSnapshot, current: MonitoringSnapshot
    ) -> bool:
        if not finding.baseline_snapshot_id or not finding.current_snapshot_id:
            finding.provenance_status = "INVALID_MISSING_SNAPSHOT_ID"
            return False

        if finding.baseline_snapshot_id != baseline.snapshot_id:
            finding.provenance_status = "INVALID_BASELINE_MISMATCH"
            return False

        if finding.current_snapshot_id != current.snapshot_id:
            finding.provenance_status = "INVALID_CURRENT_MISMATCH"
            return False

        if not finding.evidences:
            finding.provenance_status = "INVALID_MISSING_EVIDENCE"
            return False

        for ev in finding.evidences:
            if not ev.source_path:
                finding.provenance_status = "INVALID_MISSING_SOURCE_PATH"
                return False

        finding.provenance_status = "VALID"
        return True


change_provenance_engine = ChangeProvenanceEngine()
