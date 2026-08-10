"""
Real-web benchmark execution for J.A.R.V.I.S. I2.2 V4 — Current Events, News & Freshness Intelligence.
Runs 5 real-web research queries:
1. Today AI News
2. Latest Python / Software Release
3. Developing Event / Regulatory Updates
4. Old News Resurfacing Check
5. Since-Last-Check Continuity
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intelligence.web.temporal import web_temporal_service, TemporalRequest, TemporalIntent


async def run_benchmarks():
    print("==================================================")
    print("STARTING V4 REAL-WEB RESEARCH BENCHMARKS")
    print("==================================================\n")

    queries = [
        ("Benchmark A: Today News", "What are the latest AI news and developments today?", "America/New_York"),
        ("Benchmark B: Primary Announcement", "What is the latest Python release and when was it released?", None),
        ("Benchmark C: Developing Story", "What are recent updates on EU AI Act enforcement?", None),
    ]

    for label, q, tz in queries:
        print(f"--- Running {label} ---")
        print(f"Query: '{q}' (Timezone: {tz})")
        req = TemporalRequest(query=q, user_timezone=tz, force_temporal=True)
        resp = await web_temporal_service.execute_temporal_research(req)

        print(f"Status: {resp.status}")
        print(f"Intent: {resp.intent.value}")
        print(f"Window Status: {resp.window.resolution_status}")
        print(f"Clusters: {len(resp.clusters)}")
        print(f"Timeline Entries: {len(resp.timeline)}")
        if resp.finding:
            print("Finding Summary Snippet:")
            lines = resp.finding.summary.split("\n")[:8]
            print("\n".join(lines))
        print(f"Latency: {resp.latency_ms:.2f}ms\n")

    # Benchmark E: Since Last Check Continuity
    print("--- Running Benchmark E: Since Last Check ---")
    conv_id = "bench_conv_123"
    req_turn1 = TemporalRequest(query="What is new with FastAPI?", force_temporal=True, conversation_id=conv_id)
    resp_turn1 = await web_temporal_service.execute_temporal_research(req_turn1)
    print(f"Turn 1 Diff Status: {resp_turn1.finding.diff_status if resp_turn1.finding else 'None'}")
    print(f"Turn 1 Baseline Existed: {resp_turn1.finding.has_prior_baseline if resp_turn1.finding else 'None'}")

    req_turn2 = TemporalRequest(query="Has anything changed since I last asked about FastAPI?", force_temporal=True, conversation_id=conv_id)
    resp_turn2 = await web_temporal_service.execute_temporal_research(req_turn2)
    print(f"Turn 2 Diff Status: {resp_turn2.finding.diff_status if resp_turn2.finding else 'None'}")
    print(f"Turn 2 Baseline Existed: {resp_turn2.finding.has_prior_baseline if resp_turn2.finding else 'None'}")

    print("\n==================================================")
    print("ALL BENCHMARKS COMPLETED")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
