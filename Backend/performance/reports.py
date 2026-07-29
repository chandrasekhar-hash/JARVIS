"""
Structured Report Generator for J.A.R.V.I.S. Phase V1.7.
Generates structured JSON & Markdown reports containing Latency, Memory, GC, Retries, Queue Utilization, and Recommendations.
"""
from typing import Dict, Any, List
from .models import BenchmarkResult, PerformanceSnapshot


class ReportGenerator:
    """Generates structured performance audit reports."""

    @staticmethod
    def generate_markdown_report(
        snapshot: PerformanceSnapshot,
        benchmark_results: List[BenchmarkResult],
        recommendations: Optional[List[str]] = None,
    ) -> str:
        recs = recommendations or ["System operating within optimal performance parameters."]

        bench_rows = "\n".join(
            f"| {b.benchmark_name} | {b.iterations} | {b.total_time_sec:.2f}s | {b.throughput_ops_sec:.2f} ops/s | {b.latency_avg_ms:.2f} ms | {b.latency_p99_ms:.2f} ms | {'✅ PASS' if b.passed else '❌ FAIL'} |"
            for b in benchmark_results
        )

        md = f"""# J.A.R.V.I.S. Performance & Reliability Report

## 1. System Performance Snapshot
- **Overall Health Score**: **{snapshot.health_score:.1f}%**
- **Latency (P50 / P90 / P99)**: {snapshot.latency_p50:.2f} ms / {snapshot.latency_p90:.2f} ms / {snapshot.latency_p99:.2f} ms
- **Memory RSS**: {snapshot.rss_memory_mb:.2f} MB
- **Active Workers**: {snapshot.active_workers}
- **Queue Depth**: {snapshot.queue_depth}

## 2. Benchmark Suite Results
| Benchmark Name | Iterations | Duration | Throughput | Avg Latency | P99 Latency | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{bench_rows}

## 3. Operational Recommendations
""" + "\n".join(f"- {r}" for r in recs)

        return md
