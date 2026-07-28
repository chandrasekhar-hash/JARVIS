import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from Client.sync.protocol import ClientSyncEnvelope, ClientMessageType
from Client.sync.websocket_client import WebSocketSyncClient
from Client.sync.offline_store import offline_store, OfflineStore
from Client.sync.replay_queue import replay_queue, ReplayQueue
from Client.sync.conflict_handler import conflict_handler, ConflictHandler
from Client.sync.scheduler import intelligent_scheduler, SyncTrigger
from Client.sync.connection_monitor import connection_monitor, ConnectionMonitor
from Client.sync.sync_metrics import sync_metrics, SyncMetricsCollector
from Cloud.sync.crdt import crdt_engine
from Cloud.sync.delta_engine import delta_engine

logger = logging.getLogger("JARVIS_Client_SyncManager")


class ClientSyncManager:
    """
    Master ClientSyncManager entrypoint unifying WebSocket connection, offline persistence,
    operation replay buffer, CRDT conflict handler, intelligent scheduler, and metrics.
    """

    def __init__(
        self,
        store: Optional[OfflineStore] = None,
        queue: Optional[ReplayQueue] = None,
        conflicts: Optional[ConflictHandler] = None,
        monitor: Optional[ConnectionMonitor] = None,
        metrics: Optional[SyncMetricsCollector] = None
    ):
        self.store = store or offline_store
        self.queue = queue or replay_queue
        self.conflicts = conflicts or conflict_handler
        self.monitor = monitor or connection_monitor
        self.metrics = metrics or sync_metrics

        self.ws_client = WebSocketSyncClient(
            on_message_callback=self._handle_incoming_envelope,
            on_state_callback=self._on_connection_state_changed
        )
        self.user_id = ""
        self.device_id = ""
        self.sequence_counter = 0

    def initialize_client(self, user_id: str, device_id: str, access_token: str, refresh_token: str):
        self.user_id = user_id
        self.device_id = device_id
        self.ws_client.set_credentials(access_token, refresh_token, user_id, device_id)
        chk = self.store.get_checkpoint(user_id, device_id)
        if chk:
            self.sequence_counter = chk.get("last_sequence_number", 0)
        logger.info(f"ClientSyncManager initialized for user '{user_id}', device '{device_id}' (Seq: {self.sequence_counter})")

    def _on_connection_state_changed(self, new_state: str):
        self.monitor.set_state(new_state)
        if new_state == "CONNECTED":
            # Replay pending offline queue if connected
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.replay_offline_queue())
                else:
                    asyncio.run(self.replay_offline_queue())
            except Exception as e:
                logger.error(f"Error triggering offline queue replay: {e}")

    def _handle_incoming_envelope(self, envelope: ClientSyncEnvelope):
        """
        Routes and processes incoming frames from Cloud WebSocket Gateway.
        Handles ACK confirmations, DELTA patches, and CHECKPOINT updates.
        """
        logger.info(f"Received envelope type '{envelope.message_type}' from Cloud (Seq: {envelope.sequence_number})")

        # 1. Deduplication check
        msg_id = envelope.payload.get("message_id") if isinstance(envelope.payload, dict) else str(envelope.sequence_number)
        if self.queue.is_duplicate(msg_id):
            logger.info(f"Duplicate envelope '{msg_id}' suppressed.")
            return
        self.queue.mark_processed(msg_id)

        # 2. Durable ACK Processing
        if envelope.message_type == ClientMessageType.ACK:
            acked_op_id = envelope.payload.get("op_id") or envelope.payload.get("message_id")
            if acked_op_id:
                self.queue.mark_acknowledged(acked_op_id)
                self.monitor.update_pending_count(self.queue.get_pending_count())

        # 3. Delta Processing
        elif envelope.message_type == ClientMessageType.DELTA:
            self.apply_remote_delta(envelope.payload, envelope.device_id)

        # 4. Checkpoint Update
        elif envelope.message_type == ClientMessageType.CHECKPOINT:
            watermark = envelope.payload.get("stream_id", "0-0")
            self.store.save_checkpoint(self.user_id, self.device_id, envelope.sequence_number, watermark)

    def submit_local_change(self, entity_type: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches local change delta. Updates local CRDT immediately, persists op to SQLite buffer,
        and transmits envelope over active WebSocket if online.
        """
        self.sequence_counter += 1
        seq_num = self.sequence_counter

        # 1. Update local CRDT & cache immediately (Offline-First)
        if entity_type == "settings":
            self.conflicts.resolve_settings_update(changes, time.time(), self.device_id)
        elif entity_type == "memory":
            self.conflicts.resolve_memory_update(changes, time.time(), self.device_id)

        snapshot = crdt_engine.get_snapshot()
        self.store.save_entity_cache(entity_type, snapshot.get(entity_type, {}))

        # 2. Enqueue operation to SQLite pending ops buffer
        op = self.queue.enqueue_operation(entity_type, changes, seq_num)
        self.monitor.update_pending_count(self.queue.get_pending_count())

        # 3. Transmit if online
        if self.ws_client.is_connected:
            patch_wrapper = delta_engine.create_delta_patch(
                user_id=self.user_id,
                device_id=self.device_id,
                entity_type=entity_type,
                changes=changes,
                encrypt=True
            )
            patch_wrapper["op_id"] = op["message_id"]

            env = ClientSyncEnvelope(
                user_id=self.user_id,
                device_id=self.device_id,
                sequence_number=seq_num,
                message_type=ClientMessageType.DELTA,
                payload=patch_wrapper
            )
            t0 = time.time()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.ws_client.send_envelope(env))
            except Exception:
                pass
            self.metrics.record_operation((time.time() - t0) * 1000.0, bytes_up=len(str(changes)), success=True)
            return {"status": "dispatched", "op_id": op["message_id"], "sequence_number": seq_num}

        return {"status": "queued_offline", "op_id": op["message_id"], "sequence_number": seq_num}

    async def replay_offline_queue(self) -> int:
        """
        Replays enqueued offline operations over WebSocket upon network reconnection.
        Durable deletion from SQLite occurs only upon server ACK frame.
        """
        pending_ops = self.queue.drain_and_sort_queue()
        if not pending_ops:
            return 0

        replayed_count = 0
        for op in pending_ops:
            entity_type = op["entity_type"]
            changes = op["changes"]
            seq_num = op["sequence_number"]
            op_id = op["message_id"]

            if self.ws_client.is_connected:
                patch_wrapper = delta_engine.create_delta_patch(
                    user_id=self.user_id,
                    device_id=self.device_id,
                    entity_type=entity_type,
                    changes=changes,
                    encrypt=True
                )
                patch_wrapper["op_id"] = op_id

                env = ClientSyncEnvelope(
                    user_id=self.user_id,
                    device_id=self.device_id,
                    sequence_number=seq_num,
                    message_type=ClientMessageType.DELTA,
                    payload=patch_wrapper
                )
                success = await self.ws_client.send_envelope(env)
                if success:
                    replayed_count += 1

        self.metrics.record_replay(replayed_count)
        self.store.save_checkpoint(self.user_id, self.device_id, self.sequence_counter)
        self.monitor.update_sync_success(self.queue.get_pending_count())
        logger.info(f"Transmitted {replayed_count} queued offline operations for replay.")
        return replayed_count

    def apply_remote_delta(self, delta_payload: Dict[str, Any], device_source: str) -> bool:
        """
        Applies incoming remote delta patch into local CRDT and updates cache.
        """
        success, conflicts_resolved = delta_engine.apply_delta_patch(delta_payload, device_source)
        if success:
            entity_type = delta_payload.get("payload", {}).get("entity_type", "settings")
            snapshot = crdt_engine.get_snapshot()
            self.store.save_entity_cache(entity_type, snapshot.get(entity_type, {}))

            if conflicts_resolved > 0:
                self.conflicts.create_review_notification(
                    entity_type=entity_type,
                    key="remote_sync_merge",
                    local_val="Local State",
                    remote_val=delta_payload,
                    merge_res=snapshot.get(entity_type),
                    device_source=device_source
                )
        return success

    def get_status(self) -> Dict[str, Any]:
        mon_status = self.monitor.get_status()
        metrics_summary = self.metrics.get_summary()
        return {
            "connection": mon_status,
            "metrics": metrics_summary,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "sequence_counter": self.sequence_counter,
            "pending_offline_ops": self.queue.get_pending_count()
        }


client_sync_manager = ClientSyncManager()
