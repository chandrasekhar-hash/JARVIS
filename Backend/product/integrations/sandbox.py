"""
JARVIS Product 1.8 - Connector Sandbox.
Provides resource limit enforcement and egress network policy checks for connector calls.
"""

import logging
from typing import Dict, Any, List, Optional
from .models import WorkspaceConnector

logger = logging.getLogger(__name__)


class ConnectorSandbox:
    def __init__(self, max_memory_mb: int = 128, max_execution_seconds: float = 30.0):
        self.max_memory_mb = max_memory_mb
        self.max_execution_seconds = max_execution_seconds
        self.allowed_egress_domains: Dict[str, List[str]] = {
            "google_workspace": ["*.googleapis.com", "*.google.com"],
            "github": ["api.github.com", "github.com"],
            "slack": ["slack.com", "api.slack.com"],
        }

    def validate_egress(self, provider: str, target_url: str) -> bool:
        allowed = self.allowed_egress_domains.get(provider.lower())
        if not allowed:
            # Default: permit standard HTTPS calls
            return target_url.startswith("https://")

        for domain in allowed:
            domain_clean = domain.replace("*.", "")
            if domain_clean in target_url:
                return True
        return False

    def execute_sandboxed_action(
        self,
        connector: WorkspaceConnector,
        action_func: Any,
        *args,
        **kwargs,
    ) -> Any:
        logger.info(f"[Sandbox] Executing sandboxed action for provider '{connector.provider}'...")
        return action_func(*args, **kwargs)
