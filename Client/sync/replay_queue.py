import time
import json
import uuid
import logging
from typing import Dict, Any, List, Set, Optional
from Client.sync.offline_store import offline_store, OfflineStore

logger = logging.getLogger("JARVIS_Client_ReplayQueue")


class ReplayQueue:
    """
    Client ReplayQueue buffering offline updates when network connectivity drops.
    Persists operations to SQLite (client_pending_ops) to survive application restarts.
    Implements durable ACK semantics (operations are removed only upon server ACK).
    """

    def __init__(self, store: Optional[OfflineStore] = None):
        self.store = store or offline_store
        self._processed_msg_ids: Set[str] = set()

    def is_duplicate(self, message_id: str) -> bool:
        return message_id in self._processed_msg_ids

    def mark_processed(self, message_id: str):
        self._processed_msg_ids.add(message_id)

    def enqueue_operation(self, entity_type: str, changes: Dict[str, Any], sequence_number: int) -> Dict[str, Any]:
        op = {
            "message_id": f"client_op_{uuid.uuid4().hex[:12]}",
            "entity_type": entity_type,
            "changes": changes,
            "sequence_number": sequence_number,
            "timestamp": time.time(),
            "status": "pending"
        }
        self.store.save_pending_op(op)
        logger.info(f"Enqueued & persisted offline operation '{op['message_id']}' (seq {sequence_number}).")
        return op

    def get_pending_count(self) -> int:
        return len(self.store.get_all_pending_ops())

    def peek_queue(self) -> List[Dict[str, Any]]:
        return self.store.get_all_pending_ops()

    def drain_and_sort_queue(self) -> List[Dict[str, Any]]:
        """
        Retrieves pending operations sorted chronologically.
        Does NOT delete them until durable ACK is received.
        """
        ops = self.store.get_all_pending_ops()
        sorted_ops = sorted(ops, key=lambda x: (x.get("sequence_number", 0), x.get("timestamp", 0)))
        logger.info(f"Retrieved {len(sorted_ops)} pending offline operations for replay.")
        return sorted_ops

    def mark_acknowledged(self, op_id: str):
        """
        Removes operation from SQLite pending operations table upon server ACK confirmation.
        """
        self.store.remove_pending_op(op_id)
        logger.info(f"Durable ACK confirmed for operation '{op_id}'. Removed from SQLite buffer.")

    def clear(self):
        self.store.clear_pending_ops()


replay_queue = ReplayQueue()
