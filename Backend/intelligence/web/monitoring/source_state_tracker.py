"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Source Availability State Tracker.
Tracks state machine availability transitions (AVAILABLE, UNAVAILABLE, HTTP_ERROR, ACCESS_DENIED, TIMEOUT, REMOVED).
Distinguishes transient timeouts from confirmed resource removals.
"""
import logging
from typing import Tuple
from intelligence.web.monitoring.models import SourceAvailabilityStatus

logger = logging.getLogger("JARVIS_SourceStateTracker")


class SourceStateTracker:
    """
    State machine for source availability status transitions.
    """

    def determine_status_from_http(
        self, http_status: int, err_msg: Optional[str] = None
    ) -> SourceAvailabilityStatus:
        if 200 <= http_status < 400:
            return SourceAvailabilityStatus.AVAILABLE
        if http_status == 404 or http_status == 410:
            return SourceAvailabilityStatus.REMOVED
        if http_status in (401, 403):
            return SourceAvailabilityStatus.ACCESS_DENIED
        if http_status in (408, 504) or (err_msg and "timeout" in err_msg.lower()):
            return SourceAvailabilityStatus.TIMEOUT
        if http_status >= 500:
            return SourceAvailabilityStatus.HTTP_ERROR

        return SourceAvailabilityStatus.UNAVAILABLE

    def transition_state(
        self, old_state: SourceAvailabilityStatus, new_state: SourceAvailabilityStatus
    ) -> Tuple[SourceAvailabilityStatus, str]:
        if old_state == new_state:
            return new_state, f"Source state unchanged: {new_state.value}"

        logger.info(f"Source state transition: {old_state.value} -> {new_state.value}")

        if old_state == SourceAvailabilityStatus.AVAILABLE and new_state == SourceAvailabilityStatus.REMOVED:
            return new_state, "Source resource confirmed REMOVED (HTTP 404/410)."

        if old_state == SourceAvailabilityStatus.AVAILABLE and new_state == SourceAvailabilityStatus.TIMEOUT:
            return new_state, "Source experience transient TIMEOUT (not marked removed)."

        if old_state == SourceAvailabilityStatus.AVAILABLE and new_state == SourceAvailabilityStatus.ACCESS_DENIED:
            return new_state, "Source access DENIED (HTTP 401/403)."

        if old_state in (SourceAvailabilityStatus.TIMEOUT, SourceAvailabilityStatus.HTTP_ERROR, SourceAvailabilityStatus.UNAVAILABLE) and new_state == SourceAvailabilityStatus.AVAILABLE:
            return new_state, "Source availability RESTORED."

        return new_state, f"State transitioned from {old_state.value} to {new_state.value}"


source_state_tracker = SourceStateTracker()
