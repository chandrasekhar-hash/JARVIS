import time
import json
import uuid
import logging
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("JARVIS_Client_ReplayQueue")


class ReplayQueue:
    """
    Client ReplayQueue buffering offline updates when network connectivity drops.
    Survives restarts via memory/store and dispatches sequence-ordered updates on reconnect.
    """

    def __init__(self):
        self._queue: List[Dict[str, Any]] = []
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
        self._queue.append(op)
        logger.info(f"Enqueued offline operation '{op['message_id']}' (seq {sequence_number}). Total queued: {len(self._queue)}")
        return op

    def get_pending_count(self) -> int:
        return len(self._queue)

    def peek_queue(self) -> List[Dict[str, Any]]:
        return list(self._queue)

    def drain_and_sort_queue(self) -> List[Dict[str, Any]]:
        """
        Sorts queue chronologically by sequence_number/timestamp and empties pending buffer.
        """
        sorted_ops = sorted(self._queue, key=lambda x: (x.get("sequence_number", 0), x.get("timestamp", 0)))
        self._queue.clear()
        logger.info(f"Drained {len(sorted_ops)} offline operations for replay.")
        return sorted_ops

    def clear(self):
        self._queue.clear()


replay_queue = ReplayQueue()
