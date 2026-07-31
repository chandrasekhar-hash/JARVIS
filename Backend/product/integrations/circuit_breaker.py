"""
JARVIS Product 1.8 - Circuit Breaker Subsystem.
Implements a formal 3-state Circuit Breaker (CLOSED -> OPEN -> HALF_OPEN).
"""

import time
import logging
from typing import Dict, Any
from .interfaces import ICircuitBreaker
from .models import CircuitState

logger = logging.getLogger(__name__)


class CircuitBreakerManager(ICircuitBreaker):
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout_seconds: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        
        self._states: Dict[str, CircuitState] = {}
        self._consecutive_failures: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}

    def get_state(self, connector_id: str) -> CircuitState:
        state = self._states.get(connector_id, CircuitState.CLOSED)
        if state == CircuitState.OPEN:
            last_fail = self._last_failure_time.get(connector_id, 0.0)
            if time.time() - last_fail >= self.reset_timeout_seconds:
                logger.info(f"Circuit Breaker for '{connector_id}' transitioning OPEN -> HALF_OPEN (probe trial).")
                self._states[connector_id] = CircuitState.HALF_OPEN
                return CircuitState.HALF_OPEN
        return state

    def record_success(self, connector_id: str) -> None:
        self._consecutive_failures[connector_id] = 0
        current_state = self.get_state(connector_id)
        if current_state in (CircuitState.OPEN, CircuitState.HALF_OPEN):
            logger.info(f"Circuit Breaker for '{connector_id}' reset -> CLOSED (Healthy).")
            self._states[connector_id] = CircuitState.CLOSED

    def record_failure(self, connector_id: str) -> CircuitState:
        fails = self._consecutive_failures.get(connector_id, 0) + 1
        self._consecutive_failures[connector_id] = fails
        self._last_failure_time[connector_id] = time.time()

        if fails >= self.failure_threshold:
            logger.warning(f"Circuit Breaker for '{connector_id}' TRIPPED -> OPEN (Failing Fast). Failures: {fails}")
            self._states[connector_id] = CircuitState.OPEN
            return CircuitState.OPEN

        return self.get_state(connector_id)
