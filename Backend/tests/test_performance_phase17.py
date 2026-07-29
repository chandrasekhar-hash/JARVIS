"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase V1.7 Performance & Reliability Engine.
"""
import unittest
import asyncio
import time

from performance.config import PerformanceConfig
from performance.profiles import PerformanceProfileManager
from performance.models import PerformanceSnapshot, BenchmarkResult
from performance.registry import MetricsRegistry
from performance.budget import PerformanceBudget
from performance.profiler import PerformanceProfiler
from performance.task_scheduler import TaskScheduler
from performance.resource_pool import ResourcePool
from performance.queue_manager import QueueManager
from performance.cache import LRUCache
from performance.tuner import AdaptiveTuner
from performance.retry import RetryManager
from performance.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from performance.health_score import HealthScorer
from performance.memory_monitor import MemoryMonitor
from performance.engine import PerformanceEngine, performance_engine


class TestPerformanceEngineV17(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_01_profiler_latency_percentiles(self):
        profiler = PerformanceProfiler()
        for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
            profiler.record_latency("test_op", lat)

        metrics = profiler.get_metrics("test_op")
        self.assertEqual(metrics.sample_count, 5)
        self.assertEqual(metrics.min_ms, 10.0)
        self.assertEqual(metrics.max_ms, 50.0)
        self.assertEqual(metrics.avg_ms, 30.0)
        self.assertEqual(metrics.p50_ms, 30.0)
        self.assertEqual(metrics.p99_ms, 50.0)

    def test_02_performance_budget_breach_detection(self):
        budget = PerformanceBudget()

        # Under budget
        res_ok = budget.check_budget("Audio", 5.0)
        self.assertFalse(res_ok.breached)

        # Over budget (> 10ms for Audio)
        res_breach = budget.check_budget("Audio", 25.0)
        self.assertTrue(res_breach.breached)
        self.assertEqual(budget.get_summary()["total_breaches"], 1)

    def test_03_metrics_registry_primitives(self):
        reg = MetricsRegistry()
        reg.counter("requests").inc(5)
        self.assertEqual(reg.counter("requests").get(), 5.0)

        reg.gauge("active_sessions").set(12)
        self.assertEqual(reg.gauge("active_sessions").get(), 12.0)

        reg.histogram("latency").observe(100.0)
        reg.histogram("latency").observe(200.0)
        self.assertEqual(reg.histogram("latency").percentile(50), 100.0)

    def test_04_task_scheduler_priority_and_worker_scaling(self):
        async def run_test():
            scheduler = TaskScheduler(initial_workers=2, max_workers=8)
            self.assertEqual(scheduler.get_statistics().active_workers, 2)

            res = await scheduler.schedule(lambda: "done", priority=1, task_name="t1")
            self.assertEqual(res, "done")

            scheduler.adjust_worker_count(6)
            self.assertEqual(scheduler.get_statistics().active_workers, 6)

        self.loop.run_until_complete(run_test())

    def test_05_resource_pool_acquisition_and_recycling(self):
        pool = ResourcePool(factory_fn=lambda: bytearray(1024), max_size=5)

        buf1 = pool.acquire()
        self.assertEqual(len(buf1), 1024)
        stats1 = pool.get_statistics()
        self.assertEqual(stats1.in_use, 1)

        pool.release(buf1)
        stats2 = pool.get_statistics()
        self.assertEqual(stats2.in_use, 0)
        self.assertEqual(stats2.reuse_count, 1)

    def test_06_queue_manager_priority_and_overflow(self):
        async def run_test():
            qm = QueueManager(default_capacity=2)
            await qm.enqueue("test_q", "item1", priority=5)
            await qm.enqueue("test_q", "item2", priority=1)

            # Capacity full -> overflow drop
            ok = await qm.enqueue("test_q", "item3", priority=2)
            self.assertFalse(ok)

            stats = qm.get_statistics("test_q")
            self.assertEqual(stats.overflow_drops, 1)

            # Dequeue highest priority first (item2 has priority 1)
            item = await qm.dequeue("test_q")
            self.assertEqual(item, "item2")

        self.loop.run_until_complete(run_test())

    def test_07_lru_cache_ttl_and_eviction(self):
        cache = LRUCache(capacity=2, default_ttl_sec=1.0)
        cache.put("k1", "v1")
        cache.put("k2", "v2")

        self.assertEqual(cache.get("k1"), "v1")

        # Capacity eviction
        cache.put("k3", "v3")
        self.assertIsNone(cache.get("k2"))
        self.assertEqual(cache.get_statistics()["evictions"], 1)

    def test_08_adaptive_tuner_scaling(self):
        scheduler = TaskScheduler(initial_workers=4, max_workers=16)
        profiler = PerformanceProfiler()
        tuner = AdaptiveTuner(scheduler=scheduler, profiler=profiler)

        # High latency -> auto expand worker pool
        profiler.record_latency("Speech", 450.0)
        tuner.evaluate_and_tune()
        self.assertGreater(scheduler.get_statistics().active_workers, 4)

    def test_09_retry_manager_exponential_backoff(self):
        async def run_test():
            retry_mgr = RetryManager(max_retries=2, initial_delay_sec=0.01)
            attempts = 0

            def failing_fn():
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise ValueError("Transient error")
                return "success"

            res = await retry_mgr.execute_with_retry(failing_fn)
            self.assertEqual(res, "success")
            self.assertEqual(attempts, 2)

        self.loop.run_until_complete(run_test())

    def test_10_circuit_breaker_trip_and_recovery(self):
        cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_timeout_sec=0.1)
        self.assertEqual(cb.state, "CLOSED")

        cb.record_failure(ValueError("err1"))
        cb.record_failure(ValueError("err2"))
        self.assertEqual(cb.state, "OPEN")
        self.assertFalse(cb.can_execute())

        time.sleep(0.15)
        self.assertEqual(cb.state, "HALF_OPEN")
        self.assertTrue(cb.can_execute())

        cb.record_success()
        self.assertEqual(cb.state, "CLOSED")

    def test_11_health_scorer(self):
        scorer = HealthScorer()
        self.assertEqual(scorer.get_overall_score(), 100.0)

        scorer.record_score("Speech", 90.0)
        self.assertEqual(scorer.get_subsystem_score("Speech"), 90.0)
        self.assertEqual(scorer.get_overall_score(), 98.0)

    def test_12_memory_monitor_and_gc(self):
        mm = MemoryMonitor()
        stats = mm.get_statistics()
        self.assertGreaterEqual(stats.rss_mb, 0.0)

        freed = mm.force_garbage_collection()
        self.assertGreaterEqual(freed, 0)

    def test_13_performance_engine_master(self):
        async def run_test():
            engine = PerformanceEngine()
            await engine.start()

            engine.set_profile("Low Latency")
            self.assertEqual(engine.config.profile_name, "Low Latency")

            engine.profile("Audio", 4.5)
            engine.optimize()

            bench_res = await engine.benchmark(name="TestBench", iterations=10)
            self.assertTrue(bench_res.passed)

            metrics = engine.get_metrics()
            self.assertIn("snapshot", metrics)

            report = engine.generate_report([bench_res])
            self.assertIn("J.A.R.V.I.S. Performance & Reliability Report", report)

            await engine.stop()

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
