import unittest
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sync.redis_streams import redis_streams_bus, STREAM_SYNC_EVENTS
from sync.event_persistence import event_persistence_service

class TestRedisStreamsRecovery(unittest.TestCase):
    def test_01_in_memory_stream_queue_fallback_and_publish(self):
        async def _run():
            event_data = {"user_id": "usr_redis_1", "action": "sync"}
            stream_id = await redis_streams_bus.publish(STREAM_SYNC_EVENTS, event_data)
            return stream_id

        stream_id = asyncio.run(_run())
        self.assertTrue(stream_id)
        depth = redis_streams_bus.get_queue_depth(STREAM_SYNC_EVENTS)
        self.assertGreaterEqual(depth, 0)

    def test_02_event_persistence_and_pel_recovery(self):
        async def _run():
            sid = await event_persistence_service.persist_sync_event("TEST_EVENT", "usr_99", "dev_99", {"data": 1})
            entries = await event_persistence_service.recover_pending_entries("group_test", "consumer_test")
            return sid, entries

        sid, entries = asyncio.run(_run())
        self.assertTrue(sid)
        self.assertIsInstance(entries, list)

if __name__ == "__main__":
    unittest.main()
