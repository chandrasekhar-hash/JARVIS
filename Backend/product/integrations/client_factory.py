"""
JARVIS Product 1.8 - API Client Factory.
Generates authenticated REST client instances injecting SecretHandle Bearer headers and CircuitBreaker logic.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from .models import WorkspaceConnector, CircuitState
from .circuit_breaker import CircuitBreakerManager
from .rate_limiter import RateLimitManager
from .security import CredentialManager

logger = logging.getLogger(__name__)


class WorkspaceAPIClient:
    def __init__(
        self,
        connector: WorkspaceConnector,
        owner_id: str,
        credential_manager: CredentialManager,
        circuit_breaker: CircuitBreakerManager,
        rate_limiter: RateLimitManager,
    ):
        self.connector = connector
        self.owner_id = owner_id
        self.credential_manager = credential_manager
        self.circuit_breaker = circuit_breaker
        self.rate_limiter = rate_limiter

    def execute_api_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # 1. Check Circuit Breaker State
        state = self.circuit_breaker.get_state(self.connector.connector_id)
        if state == CircuitState.OPEN:
            raise RuntimeError(f"Circuit Breaker for provider '{self.connector.provider}' is OPEN. Fast failing API request.")

        # 2. Check Rate Limits
        if not self.rate_limiter.check_rate_limit(self.connector.provider, self.connector.rate_limits):
            raise RuntimeError(f"Rate limit quota exceeded for provider '{self.connector.provider}'.")

        # 3. Resolve SecretHandle
        secret_ref = self.connector.secret_handle.secret_ref if self.connector.secret_handle else ""
        creds = self.credential_manager.resolve_secret_handle(secret_ref, self.owner_id)
        if not creds:
            self.circuit_breaker.record_failure(self.connector.connector_id)
            raise PermissionError(f"Failed to resolve SecretHandle '{secret_ref}' for user '{self.owner_id}'.")

        # Execute simulated API call
        self.circuit_breaker.record_success(self.connector.connector_id)
        return {
            "status_code": 200,
            "provider": self.connector.provider,
            "endpoint": endpoint,
            "data": {"message": f"Successfully executed {method} {endpoint}"},
        }


class APIClientFactory:
    def __init__(
        self,
        credential_manager: CredentialManager,
        circuit_breaker: CircuitBreakerManager,
        rate_limiter: RateLimitManager,
    ):
        self.credential_manager = credential_manager
        self.circuit_breaker = circuit_breaker
        self.rate_limiter = rate_limiter

    def get_client(self, connector: WorkspaceConnector, owner_id: str) -> WorkspaceAPIClient:
        return WorkspaceAPIClient(
            connector=connector,
            owner_id=owner_id,
            credential_manager=self.credential_manager,
            circuit_breaker=self.circuit_breaker,
            rate_limiter=self.rate_limiter,
        )
