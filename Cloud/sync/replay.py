import time
import logging
from typing import Dict, Any, List, Set, Optional
from sync.checkpoint import checkpoint_manager, CheckpointMetadata

logger = logging.getLogger("JARVIS_Cloud_Replay")


class ReplayEngine:
    """
    Offline Replay Engine queueing updates, preserving sequence number order,
    replaying missing events after reconnect, and discarding duplicate messages.
    """

    def __init__(self):
        # device_id -> List of SyncMessageEnvelopes / payload dicts
        self.offline_queues: Dict[str, List[Dict[str, Any]]] = {}
        # Track processed message IDs to guarantee idempotent deduplication
        self.processed_message_ids: Set[str] = set()

    def is_duplicate(self, message_id: str) -> bool:
        return message_id in self.processed_message_ids

    def mark_processed(self, message_id: str):
        self.processed_message_ids.add(message_id)
        # Cap set size to prevent RAM leaks
        if len(self.processed_message_ids) > 10000:
            self.processed_message_ids.clear()

    def queue_offline_update(self, device_id: str, message_payload: Dict[str, Any]):
        if device_id not in self.offline_queues:
            self.offline_queues[device_id] = []
        self.offline_queues[device_id].append(message_payload)
        logger.info(f"Queued offline update for device '{device_id}'. Total queued: {len(self.offline_queues[device_id])}")

    def get_offline_queue_depth(self, device_id: Optional[str] = None) -> int:
        if device_id:
            return len(self.offline_queues.get(device_id, []))
        return sum(len(q) for q in self.offline_queues.values())

    def replay_offline_events(self, user_id: str, device_id: str) -> List[Dict[str, Any]]:
        """
        Replays queued events in strict sequence_number order resuming from last checkpoint.
        """
        queue = self.offline_queues.get(device_id, [])
        if not queue:
            return []

        # Sort queue chronologically by sequence_number or timestamp
        queue.sort(key=lambda x: (x.get("sequence_number", 0), x.get("timestamp", 0)))

        checkpoint = checkpoint_manager.get_checkpoint(user_id, device_id)
        last_seq = checkpoint.last_sequence_number if checkpoint else 0

        replayed_events = []
        for event in queue:
            msg_id = event.get("message_id", "")
            seq_num = event.get("sequence_number", 0)

            # Skip duplicate or already processed events
            if msg_id and self.is_duplicate(msg_id):
                continue

            if seq_num > last_seq:
                replayed_events.append(event)
                if msg_id:
                    self.mark_processed(msg_id)

        # Clear processed queue for device
        self.offline_queues[device_id] = []
        logger.info(f"Replayed {len(replayed_events)} offline events for device '{device_id}'")
        return replayed_events


replay_engine = ReplayEngine()
