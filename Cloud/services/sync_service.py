import time
import logging
from typing import Dict, Any, Optional, Tuple
from websocket.protocol import SyncMessageEnvelope, MessageType
from websocket.connection import WSConnection
from websocket.state_machine import ConnectionState
from websocket.manager import ws_manager
from sync.crdt import crdt_engine
from sync.delta_engine import delta_engine
from sync.checkpoint import checkpoint_manager, CheckpointMetadata
from sync.replay import replay_engine
from sync.encryption import payload_encryptor
from sync.event_persistence import event_persistence_service
from services.presence_service import presence_service

logger = logging.getLogger("JARVIS_Cloud_SyncService")


class SyncService:
    """
    High-level SyncService orchestrating WebSocket routing, CRDT state merges, delta generation,
    replay recovery, presence tracking, delegating stream persistence to EventPersistenceService.
    """

    async def handle_incoming_envelope(self, conn: WSConnection, envelope: SyncMessageEnvelope) -> Optional[SyncMessageEnvelope]:
        msg_type = envelope.message_type
        user_id = envelope.user_id or conn.user_id
        device_id = envelope.device_id or conn.device_id

        # Deduplication check
        if replay_engine.is_duplicate(envelope.message_id):
            logger.info(f"Duplicate message '{envelope.message_id}' ignored.")
            return None
        replay_engine.mark_processed(envelope.message_id)

        # Update WS ping timestamp
        conn.update_ping()

        # Handle Message Types
        if msg_type == MessageType.PING:
            return SyncMessageEnvelope(
                user_id=user_id,
                device_id=device_id,
                session_id=conn.session_id,
                sequence_number=conn.next_sequence_number(),
                message_type=MessageType.PONG,
                payload={"reply_timestamp": time.time()}
            )

        elif msg_type == MessageType.SYNC_REQUEST:
            conn.transition_to(ConnectionState.SYNCHRONIZING)
            # Replay any queued offline events
            replayed = replay_engine.replay_offline_events(user_id, device_id)
            crdt_snapshot = crdt_engine.get_snapshot()

            conn.transition_to(ConnectionState.ACTIVE)
            await presence_service.update_presence(device_id, user_id, "ACTIVE")

            # Persist sync request event
            await event_persistence_service.persist_sync_event("SYNC_REQUEST", user_id, device_id, envelope.payload)

            return SyncMessageEnvelope(
                user_id=user_id,
                device_id=device_id,
                session_id=conn.session_id,
                sequence_number=conn.next_sequence_number(),
                message_type=MessageType.SYNC_RESPONSE,
                payload={
                    "replayed_events_count": len(replayed),
                    "crdt_snapshot": crdt_snapshot,
                    "watermark": time.time()
                }
            )

        elif msg_type == MessageType.DELTA:
            # Apply incoming delta patch into CRDT
            success, conflicts_resolved = delta_engine.apply_delta_patch(envelope.payload, device_id)

            # Update checkpoint watermark
            checkpoint = CheckpointMetadata(
                user_id=user_id,
                device_id=device_id,
                last_sequence_number=envelope.sequence_number,
                timestamp=time.time()
            )
            checkpoint_manager.save_checkpoint(checkpoint)

            # Persist delta event
            stream_id = await event_persistence_service.persist_sync_event("DELTA_APPLIED", user_id, device_id, envelope.payload)

            # Broadcast updated delta patch to other user devices
            broadcast_env = SyncMessageEnvelope(
                user_id=user_id,
                device_id=device_id,
                sequence_number=conn.next_sequence_number(),
                message_type=MessageType.DELTA,
                payload=envelope.payload
            )
            await ws_manager.broadcast(broadcast_env, exclude_device_id=device_id)

            return SyncMessageEnvelope(
                user_id=user_id,
                device_id=device_id,
                session_id=conn.session_id,
                sequence_number=conn.next_sequence_number(),
                message_type=MessageType.ACK,
                payload={
                    "ack_message_id": envelope.message_id,
                    "stream_id": stream_id,
                    "conflicts_resolved": conflicts_resolved,
                    "status": "success" if success else "failed"
                }
            )

        return None


sync_service = SyncService()
