"""
Multi-Tenant Ephemeral Session State Manager for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
import time
from typing import Dict, Optional, Tuple, Any
from intelligence.web.decision.models import DecisionWebResponse


class DecisionStateManager:
    """
    Manages ephemeral multi-tenant decision session state with 3600s TTL and scope isolation.
    Keyed by (owner_scope_id, conversation_id, decision_session_id).
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[Tuple[str, str, str], Tuple[float, DecisionWebResponse]] = {}

    def get_state(
        self, owner_scope_id: Optional[str], conversation_id: Optional[str], session_id: Optional[str]
    ) -> Optional[DecisionWebResponse]:
        if not owner_scope_id or not conversation_id or not session_id:
            return None

        key = (owner_scope_id, conversation_id, session_id)
        entry = self._store.get(key)
        if not entry:
            return None

        ts, resp = entry
        if time.time() - ts > self.ttl_seconds:
            del self._store[key]
            return None

        return resp

    def set_state(
        self,
        owner_scope_id: Optional[str],
        conversation_id: Optional[str],
        session_id: Optional[str],
        response: DecisionWebResponse,
    ):
        if not owner_scope_id or not conversation_id or not session_id:
            return

        # Evict old entries if store grows large
        if len(self._store) > 100:
            now = time.time()
            expired = [k for k, (ts, _) in self._store.items() if now - ts > self.ttl_seconds]
            for k in expired:
                del self._store[k]

        key = (owner_scope_id, conversation_id, session_id)
        self._store[key] = (time.time(), response)


decision_state_manager = DecisionStateManager()
