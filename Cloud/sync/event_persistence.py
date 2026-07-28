import time
import logging
from typing import Dict, Any, List, Optional
from sync.redis_streams import redis_streams_bus, STREAM_SYNC_EVENTS, STREAM_DEVICE_EVENTS, STREAM_TELEMETRY_EVENTS

logger = logging.getLogger("JARVIS_Cloud_EventPersistence")


class EventPersistenceService:
    """
    Decoupled Event Persistence Service handling Redis Streams interaction, stream acknowledgements (XACK),
    PEL pending entries recovery, and retries independently from sync orchestration.
    """

    async def persist_sync_event(self, event_type: str, user_id: str, device_id: str, payload: Dict[str, Any]) -> str:
        event = {
            "event_type": event_type,
            "user_id": user_id,
            "device_id": device_id,
            "payload": payload,
            "timestamp": time.time()
        }
        stream_id = await redis_streams_bus.publish(STREAM_SYNC_EVENTS, event)
        logger.debug(f"Persisted sync event '{event_type}' to stream ID {stream_id}")
        return stream_id

    async def persist_device_event(self, event_type: str, device_id: str, details: Dict[str, Any]) -> str:
        event = {
            "event_type": event_type,
            "device_id": device_id,
            "details": details,
            "timestamp": time.time()
        }
        return await redis_streams_bus.publish(STREAM_DEVICE_EVENTS, event)

    async def acknowledge_event(self, stream_name: str, group_name: str, stream_id: str) -> bool:
        return await redis_streams_bus.ack(stream_name, group_name, stream_id)

    async def recover_pending_entries(self, group_name: str, consumer_name: str) -> List[Dict[str, Any]]:
        """
        Scans Pending Entries List (PEL) to recover unacknowledged messages after worker restart.
        """
        logger.info(f"Recovering pending entries for consumer '{consumer_name}' in group '{group_name}'")
        return await redis_streams_bus.consume_group(STREAM_SYNC_EVENTS, group_name, consumer_name, count=50)


event_persistence_service = EventPersistenceService()
