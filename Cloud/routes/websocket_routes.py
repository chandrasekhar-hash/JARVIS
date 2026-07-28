import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from websocket.connection import WSConnection
from websocket.state_machine import ConnectionState
from websocket.authentication import authenticate_websocket_connection
from websocket.manager import ws_manager
from websocket.protocol import SyncMessageEnvelope, MessageType
from services.sync_service import sync_service
from services.presence_service import presence_service

logger = logging.getLogger("JARVIS_Cloud_WSRoutes")

router = APIRouter(tags=["Cloud WebSocket Gateway"])


@router.websocket("/ws/sync")
async def websocket_sync_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    conn = WSConnection(websocket)
    await ws_manager.connect(conn)

    # 1. Wait for AUTH or query token
    auth_success = False

    if token:
        auth_success, payload, reason = authenticate_websocket_connection(conn, token)
        if auth_success:
            ws_manager.register_authenticated_session(conn)
            await presence_service.update_presence(conn.device_id, conn.user_id, "CONNECTED")
            auth_ok_env = SyncMessageEnvelope(
                user_id=conn.user_id,
                device_id=conn.device_id,
                session_id=conn.session_id,
                sequence_number=conn.next_sequence_number(),
                message_type=MessageType.AUTH_OK,
                payload={"status": "authenticated", "reason": reason}
            )
            await ws_manager.send_envelope(conn, auth_ok_env)

    try:
        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)
            envelope = SyncMessageEnvelope(**data)

            # Handle AUTH message if not yet authenticated
            if envelope.message_type == MessageType.AUTH:
                auth_token = envelope.payload.get("token") or token
                proto_ver = envelope.protocol_version
                auth_success, payload, reason = authenticate_websocket_connection(conn, auth_token, proto_ver)

                if auth_success:
                    ws_manager.register_authenticated_session(conn)
                    await presence_service.update_presence(conn.device_id, conn.user_id, "CONNECTED")
                    auth_ok_env = SyncMessageEnvelope(
                        user_id=conn.user_id,
                        device_id=conn.device_id,
                        session_id=conn.session_id,
                        sequence_number=conn.next_sequence_number(),
                        message_type=MessageType.AUTH_OK,
                        payload={"status": "authenticated", "reason": reason}
                    )
                    await ws_manager.send_envelope(conn, auth_ok_env)
                else:
                    err_env = SyncMessageEnvelope(
                        message_type=MessageType.ERROR,
                        payload={"error": "AUTH_FAILED", "detail": reason}
                    )
                    await ws_manager.send_envelope(conn, err_env)
                    await ws_manager.disconnect(conn)
                    break
                continue

            # Reject unauthenticated traffic
            if conn.state not in [ConnectionState.ACTIVE, ConnectionState.SYNCHRONIZING, ConnectionState.IDLE]:
                err_env = SyncMessageEnvelope(
                    message_type=MessageType.ERROR,
                    payload={"error": "UNAUTHENTICATED", "detail": "Must send AUTH envelope before dispatching commands."}
                )
                await ws_manager.send_envelope(conn, err_env)
                await ws_manager.disconnect(conn)
                break

            # Handle authenticated envelope
            reply_env = await sync_service.handle_incoming_envelope(conn, envelope)
            if reply_env:
                await ws_manager.send_envelope(conn, reply_env)

    except WebSocketDisconnect:
        logger.info(f"WS [{conn.connection_id}] Client disconnected cleanly.")
    except Exception as e:
        logger.error(f"WS [{conn.connection_id}] Error in connection loop: {e}")
    finally:
        if conn.device_id:
            await presence_service.update_presence(conn.device_id, conn.user_id, "OFFLINE")
        await ws_manager.disconnect(conn)
