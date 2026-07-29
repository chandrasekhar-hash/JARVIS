"""
Circuit Breaker Pattern Engine for J.A.R.V.I.S. Phase V1.7.
Protects subsystems against cascading failures using CLOSED, OPEN, HALF_OPEN states.
"""
import time
import logging
from typing import Dict, Any
from .interfaces import ICircuitBreaker
from .models import CircuitBreakerStatistics

logger = logging.getLogger("JARVIS_CircuitBreaker")


class CircuitBreakerOpenError(Exception):
    """Exception raised when execution is attempted on an OPEN circuit breaker."""
    pass


class CircuitBreaker(ICircuitBreaker):
    """
    Circuit Breaker pattern protecting downstream subsystem operations.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout_sec: float = 10.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec

        self._state: str = "CLOSED"
        self._failure_count: int = 0
        self._success_count: int = 0
        self._trip_count: int = 0
        self._last_state_change: float = time.time()

    @property
    def state(self) -> str:
        # Check if OPEN state recovery timeout has expired -> HALF_OPEN
        if self._state == "OPEN":
            if time.time() - self._last_state_change > self.recovery_timeout_sec:
                self._state = "HALF_OPEN"
                self._last_state_change = time.time()
                logger.info(f"[CircuitBreaker '{self.name}'] Recovery timeout expired. Transitioned: OPEN -> HALF_OPEN.")
        return self._state

    def can_execute(self) -> bool:
        return self.state in ("CLOSED", "HALF_OPEN")

    def record_success(self) -> None:
        self._success_count += 1
        if self.state == "HALF_OPEN":
            self._state = "CLOSED"
            self._failure_count = 0
            self._last_state_change = time.time()
            logger.info(f"[CircuitBreaker '{self.name}'] Success in HALF_OPEN. Circuit CLOSED.")
        elif self.state == "CLOSED":
            self._failure_count = 0

    def record_failure(self, error: Exception) -> None:
        self._failure_count += 1
        logger.warning(f"[CircuitBreaker '{self.name}'] Failure recorded ({self._failure_count}/{self.failure_threshold}): {error}")

        if self._failure_count >= self.failure_threshold or self.state == "HALF_OPEN":
            self._state = "OPEN"
            self._trip_count += 1
            self._last_state_change = time.time()
            logger.error(f"[CircuitBreaker '{self.name}'] Failure threshold reached. Circuit TRIP -> OPEN.")

    def get_statistics(self) -> CircuitBreakerStatistics:
        return CircuitBreakerStatistics(
            state=self.state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            trip_count=self._trip_count,
            last_state_change=self._last_state_change,
        )
