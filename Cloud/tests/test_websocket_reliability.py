import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app
from websocket.connection import WSConnection
from websocket.authentication import authenticate_websocket_connection
from websocket.state_machine import ConnectionState
from websocket.manager import ws_manager

class TestWebSocketReliability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_reject_invalid_token(self):
        # Connecting with bogus JWT token should fail authentication
        class FakeWS:
            pass
        conn = WSConnection(FakeWS())
        success, payload, reason = authenticate_websocket_connection(conn, "invalid_jwt_token_123")
        self.assertFalse(success)
        self.assertIn("Invalid or expired", reason)
        self.assertEqual(conn.state, ConnectionState.DISCONNECTED)

    def test_02_reject_unsupported_protocol_version(self):
        class FakeWS:
            pass
        conn = WSConnection(FakeWS())
        success, payload, reason = authenticate_websocket_connection(conn, "valid_token", protocol_version="1.0")
        self.assertFalse(success)
        self.assertIn("Unsupported protocol version", reason)
        self.assertEqual(conn.state, ConnectionState.DISCONNECTED)

    def test_03_zero_session_leaks_after_disconnect(self):
        initial_active = len(ws_manager.active_connections)
        class FakeWS:
            async def close(self): pass
        conn = WSConnection(FakeWS())
        conn.connection_id = "conn_leak_test_99"

        ws_manager.active_connections[conn.connection_id] = conn
        self.assertEqual(len(ws_manager.active_connections), initial_active + 1)

        # Disconnect connection
        import asyncio
        asyncio.run(ws_manager.disconnect(conn))
        self.assertEqual(len(ws_manager.active_connections), initial_active)

if __name__ == "__main__":
    unittest.main()
