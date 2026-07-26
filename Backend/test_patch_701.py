import os
import sys
import time
import asyncio
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain.event_bus import EventBus
from common.cache import MemoryCacheProvider, CacheManager, BaseCacheProvider


class TestPatch701(unittest.IsolatedAsyncioTestCase):

    async def test_event_bus_bounded_queue_overflow(self):
        # Create EventBus with a small queue bound for testing
        bus = EventBus(max_history=5, max_queue_size=10, listener_timeout_sec=1.0)

        # Emit 15 events to force overflow
        for i in range(15):
            bus.emit("TestOverflowEvent", item_id=i)

        metrics = bus.get_metrics()
        self.assertEqual(metrics["total_emitted"], 15)
        self.assertGreater(metrics["total_dropped"], 0)
        self.assertLessEqual(metrics["current_queue_size"], 10)

    async def test_event_bus_async_listener_timeout_resilience(self):
        bus = EventBus(listener_timeout_sec=0.1)

        async def slow_listener(event):
            await asyncio.sleep(0.5)  # Exceeds 0.1s timeout

        bus.subscribe("TimeoutEvent", slow_listener)
        bus.emit("TimeoutEvent")

        # Allow async event task to execute
        await asyncio.sleep(0.2)

        metrics = bus.get_metrics()
        self.assertGreater(metrics["total_errors"], 0)

    async def test_memory_cache_provider_crud_and_ttl(self):
        cache = MemoryCacheProvider(default_ttl_sec=1.0)

        # Set and get
        self.assertTrue(cache.set("k1", "v1", ttl_sec=0.2))
        self.assertTrue(cache.exists("k1"))
        self.assertEqual(cache.get("k1"), "v1")

        # Check TTL remaining
        ttl_rem = cache.ttl("k1")
        self.assertGreater(ttl_rem, 0.0)

        # Wait for expiration
        await asyncio.sleep(0.25)
        self.assertFalse(cache.exists("k1"))
        self.assertIsNone(cache.get("k1"))

        # Telemetry statistics
        stats = cache.statistics()
        self.assertGreater(stats["misses"], 0)
        self.assertGreater(stats["evictions"], 0)

    async def test_cache_manager_delegation_and_swapping(self):
        manager = CacheManager()

        manager.set("k2", "v2")
        self.assertEqual(manager.get("k2"), "v2")
        self.assertTrue(manager.exists("k2"))

        stats = manager.statistics()
        self.assertEqual(stats["total_keys"], 1)

        # Swapping provider
        new_provider = MemoryCacheProvider()
        manager.set_provider(new_provider)

        # New provider starts fresh
        self.assertFalse(manager.exists("k2"))
        manager.set("k3", "v3")
        self.assertEqual(manager.get("k3"), "v3")

    async def test_cache_clear_and_delete(self):
        cache = MemoryCacheProvider()
        cache.set("a", 1)
        cache.set("b", 2)

        self.assertTrue(cache.delete("a"))
        self.assertFalse(cache.exists("a"))

        self.assertTrue(cache.clear())
        self.assertFalse(cache.exists("b"))
        self.assertEqual(len(cache._store), 0)


if __name__ == "__main__":
    unittest.main()
