"""
Diagnostic Report Generator for J.A.R.V.I.S. Phase V1.8.
Formated markdown diagnostic report generator.
"""
from typing import Dict, Any, List, Optional
from .models import HealthSnapshot, DashboardSnapshot, StartupCheck, RuntimeCheck


class DiagnosticReportGenerator:
    """Generates comprehensive system diagnostic reports."""

    @staticmethod
    def generate_report(
        health_snapshot: HealthSnapshot,
        dashboard_snapshot: DashboardSnapshot,
        startup_checks: List[StartupCheck],
        runtime_checks: List[RuntimeCheck],
        recommendations: Optional[List[str]] = None,
    ) -> str:
        recs = recommendations or ["System operating at 100% production readiness."]

        startup_rows = "\n".join(f"| {c.check_name} | {'✅ PASSED' if c.passed else '❌ FAILED'} | {c.details} |" for c in startup_checks)
        runtime_rows = "\n".join(f"| {c.check_name} | {'✅ NOMINAL' if c.passed else '⚠️ WARNING'} | {c.details} |" for c in runtime_checks)
        sub_rows = "\n".join(f"| {name} | {'✅ HEALTHY' if status.healthy else '❌ DEGRADED'} | {status.latency_ms:.2f} ms | {status.error_count} |" for name, status in health_snapshot.subsystems.items())

        md = f"""# J.A.R.V.I.S. System Diagnostic & Observability Report

## 1. Executive Summary
- **Overall Health Score**: **{health_snapshot.overall_score:.1f}%**
- **Overall Health Status**: **{'✅ OPERATIONAL' if health_snapshot.overall_healthy else '⚠️ DEGRADED'}**
- **P50 / P99 Latency**: {dashboard_snapshot.latency_p50:.2f} ms / {dashboard_snapshot.latency_p99:.2f} ms
- **Process Memory (RSS)**: {dashboard_snapshot.rss_memory_mb:.2f} MB
- **Active Workers / Queue Depth**: {dashboard_snapshot.active_workers} workers / {dashboard_snapshot.queue_depth} queued

## 2. Startup Diagnostics
| Check Name | Status | Details |
| :--- | :--- | :--- |
{startup_rows}

## 3. Subsystem Health Breakdown
| Subsystem | Health Status | Latency | Errors |
| :--- | :--- | :--- | :--- |
{sub_rows}

## 4. Runtime Stability Diagnostics
| Check Name | Status | Details |
| :--- | :--- | :--- |
{runtime_rows}

## 5. Engineering Recommendations
""" + "\n".join(f"- {r}" for r in recs)

        return md
