import unittest
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from Client.sync.websocket_client import WebSocketSyncClient
from Client.sync.connection_monitor import ConnectionMonitor

class TestReconnectAndMonitor(unittest.TestCase):
    def test_01_connection_monitor_state_listener(self):
        monitor = ConnectionMonitor()
        state_changes = []

        def listener(status):
            state_changes.append(status["state"])

        monitor.register_listener(listener)
        monitor.set_state("CONNECTING")
        monitor.set_state("CONNECTED")
        monitor.set_state("OFFLINE")

        self.assertEqual(state_changes, ["CONNECTING", "CONNECTED", "OFFLINE"])

    def test_02_websocket_client_credentials_and_sequence(self):
        ws_client = WebSocketSyncClient()
        ws_client.set_credentials("token_access_123", "token_refresh_456", "usr_1", "dev_1")
        self.assertEqual(ws_client.access_token, "token_access_123")
        self.assertEqual(ws_client.get_next_sequence_number(), 1)
        self.assertEqual(ws_client.get_next_sequence_number(), 2)

if __name__ == "__main__":
    unittest.main()
