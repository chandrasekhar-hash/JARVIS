import asyncio
import time
import logging
from websocket.manager import ws_manager
from websocket.protocol import SyncMessageEnvelope, MessageType
from websocket.state_machine import ConnectionState

logger = logging.getLogger("JARVIS_Cloud_WSHeartbeat")


class HeartbeatMonitor:
    def __init__(self, ping_interval: float = 15.0, idle_timeout: float = 45.0):
        self.ping_interval = ping_interval
        self.idle_timeout = idle_timeout
        self._running = False
        self._task: asyncio.Task = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("HeartbeatMonitor started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("HeartbeatMonitor stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self.ping_interval)
                now = time.time()
                connections = list(ws_manager.active_connections.values())

                for conn in connections:
                    # Idle timeout check
                    if now - conn.last_ping > self.idle_timeout:
                        logger.warning(f"WS [{conn.connection_id}] Exceeded idle timeout ({self.idle_timeout}s). Disconnecting.")
                        await ws_manager.disconnect(conn)
                        continue

                    # Send Ping frame
                    ping_env = SyncMessageEnvelope(
                        user_id=conn.user_id,
                        device_id=conn.device_id,
                        session_id=conn.session_id,
                        sequence_number=conn.next_sequence_number(),
                        message_type=MessageType.PING,
                        payload={"ping_timestamp": now}
                    )
                    await ws_manager.send_envelope(conn, ping_env)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")


heartbeat_monitor = HeartbeatMonitor()
