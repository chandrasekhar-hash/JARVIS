"""
Product 1.5 Execution Context Factory and Context Injector.
"""
import uuid
import time
import logging
from typing import Dict, Any, Optional
from .models import ExecutionContext

logger = logging.getLogger("JARVIS_ExecutionContextFactory")


class ExecutionContextFactory:
    """
    Factory for instantiating thread-safe, immutable ExecutionContext objects
    populated with user, session, security, memory, settings, and correlation metadata.
    """

    @staticmethod
    def create_context(
        tool_id: str,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        security_context: Optional[Any] = None,
        user_preferences: Optional[Any] = None,
        memory_provider: Optional[Any] = None,
        plugin_reference: Optional[Any] = None,
        correlation_id: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionContext:
        """Constructs an ExecutionContext instance."""
        corr_id = correlation_id or f"exec_{uuid.uuid4().hex[:12]}"
        meta = request_metadata or {}

        ctx = ExecutionContext(
            correlation_id=corr_id,
            tool_id=tool_id,
            user_id=user_id,
            session_id=session_id,
            security_context=security_context,
            user_preferences=user_preferences,
            memory_provider=memory_provider,
            plugin_reference=plugin_reference,
            request_metadata=meta,
            created_at=time.time(),
        )

        logger.debug(f"[ExecutionContextFactory] Built ExecutionContext '{corr_id}' for tool '{tool_id}' (User: {user_id}).")
        return ctx
