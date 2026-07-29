"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase V1.8 Diagnostics Platform.
"""
import os
import unittest
import asyncio

from diagnostics.config import DiagnosticsConfig
from diagnostics.models import LogEntry, TraceRecord, TimelineRecord, HealthSnapshot, DashboardSnapshot
from diagnostics.logger import StructuredLogger
from diagnostics.tracer import DistributedTracer
from diagnostics.timeline import TimelineRecorder
from diagnostics.health import HealthChecker
from diagnostics.startup import StartupValidator
from diagnostics.runtime import RuntimeDiagnosticMonitor
from diagnostics.dashboard import DashboardGenerator
from diagnostics.metrics_bridge import MetricsBridge
from diagnostics.exporters import DiagnosticsExporter
from diagnostics.report import DiagnosticReportGenerator
from diagnostics.engine import DiagnosticsEngine, diagnostics_engine


class TestDiagnosticsEngineV18(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_01_structured_logger_context_and_levels(self):
        logger = StructuredLogger(config=DiagnosticsConfig(enable_file_logging=False))
        logger.info("Speech", "STT initialized", correlation_id="cor_123", mode="streaming")
        logger.error("Audio", "Frame dropped", correlation_id="cor_123", frame_id=42)

        logs = logger.get_logs(limit=10)
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].level, "INFO")
        self.assertEqual(logs[0].subsystem, "Speech")
        self.assertEqual(logs[0].context["mode"], "streaming")
        self.assertEqual(logs[1].level, "ERROR")

    def test_02_distributed_tracer_spans_and_durations(self):
        tracer = DistributedTracer()
        trace = tracer.start_trace("VoiceRequest", correlation_id="cor_trc")

        span1 = tracer.start_span(trace.trace_id, "SpeechRecognition")
        time_start = span1.started_at
        tracer.finish_span(span1.span_id, metadata={"words": 5})

        fetched_trace = tracer.get_trace(trace.trace_id)
        self.assertIsNotNone(fetched_trace)
        self.assertEqual(len(fetched_trace.spans), 1)
        self.assertGreaterEqual(fetched_trace.total_duration_ms, 0.0)

    def test_03_timeline_recorder_and_replay(self):
        recorder = TimelineRecorder()
        recorder.record_event("WakeWordDetected", "WakeWord", session_id="ses_101", confidence=0.98)
        recorder.record_event("TranscriptReady", "Speech", session_id="ses_101", text="Hello")

        timeline = recorder.get_timeline(session_id="ses_101")
        self.assertEqual(len(timeline), 2)

        replay = recorder.replay_timeline(session_id="ses_101")
        self.assertEqual(len(replay), 2)
        self.assertEqual(replay[0].event_type, "WakeWordDetected")
        self.assertEqual(replay[1].event_type, "TranscriptReady")

    def test_04_health_checker_status(self):
        hc = HealthChecker()
        hc.record_subsystem_health("Speech", healthy=True, latency_ms=120.0)
        hc.record_subsystem_health("Audio", healthy=False, error_count=2)

        snap = hc.check_health()
        self.assertFalse(snap.overall_healthy)
        self.assertIn("Speech", snap.subsystems)
        self.assertTrue(snap.subsystems["Speech"].healthy)
        self.assertFalse(snap.subsystems["Audio"].healthy)

    def test_05_startup_and_runtime_validators(self):
        startup_checks = StartupValidator.run_all_checks()
        self.assertGreater(len(startup_checks), 0)
        self.assertTrue(all(c.passed for c in startup_checks))

        runtime_checks = RuntimeDiagnosticMonitor.run_runtime_checks()
        self.assertGreater(len(runtime_checks), 0)

    def test_06_dashboard_generator(self):
        dg = DashboardGenerator()
        snap = dg.get_snapshot()
        self.assertEqual(snap.health_score, 100.0)
        self.assertGreater(snap.rss_memory_mb, 0.0)

    def test_07_metrics_bridge(self):
        mb = MetricsBridge()
        snapshot = mb.read_metrics_snapshot()
        self.assertIn("counters", snapshot)
        self.assertIn("gauges", snapshot)

    def test_08_diagnostics_exporter(self):
        exporter = DiagnosticsExporter(config=DiagnosticsConfig(export_directory="logs/test_exports"))
        data = [{"id": 1, "status": "ok"}, {"id": 2, "status": "error"}]

        json_path = exporter.export_json(data, "logs/test_exports/test.json")
        self.assertTrue(os.path.exists(json_path))

        csv_path = exporter.export_csv(data, "logs/test_exports/test.csv")
        self.assertTrue(os.path.exists(csv_path))

        # Cleanup test exports
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(csv_path):
            os.remove(csv_path)

    def test_09_diagnostics_engine_master_api(self):
        async def run_test():
            engine = DiagnosticsEngine()
            await engine.start()

            engine.log("INFO", "Test", "Engine test message")
            trc = engine.trace("RootOp")
            engine.timeline()

            dash = engine.dashboard()
            self.assertEqual(dash.health_score, 100.0)

            health = engine.health()
            self.assertTrue(health.overall_healthy)

            report = engine.generate_report()
            self.assertIn("J.A.R.V.I.S. System Diagnostic & Observability Report", report)

            await engine.stop()

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
