import time
import logging
from typing import Dict, Any

logger = logging.getLogger("JARVIS_CircuitBreaker")


class CircuitBreaker:
    """
    Provider CircuitBreaker pattern tracking failure rates and controlling failover state.
    States: CLOSED (Normal), OPEN (Failing/Tripped), HALF_OPEN (Testing recovery).
    """

    def __init__(self, provider_name: str, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_state_change = time.time()

    def allow_request(self) -> bool:
        now = time.time()
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if now - self.last_state_change > self.recovery_timeout:
                logger.info(f"CircuitBreaker for '{self.provider_name}' entering HALF_OPEN recovery test.")
                self.state = "HALF_OPEN"
                self.last_state_change = now
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False

    def record_success(self):
        if self.state in ["HALF_OPEN", "OPEN"]:
            logger.info(f"CircuitBreaker for '{self.provider_name}' recovered to CLOSED.")
        self.state = "CLOSED"
        self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        logger.warning(f"CircuitBreaker for '{self.provider_name}' failure recorded ({self.failure_count}/{self.failure_threshold}).")
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()
            logger.error(f"CircuitBreaker for '{self.provider_name}' TRIPPED to OPEN state! Blocking requests for {self.recovery_timeout}s.")

    def get_status(self) -> Dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "state": self.state,
            "failure_count": self.failure_count,
            "last_state_change": self.last_state_change
        }
