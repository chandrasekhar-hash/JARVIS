import asyncio
import time
from intelligence.web.research import web_research_service, ResearchRequest, ResearchIntent

async def run_benchmarks():
    print("==================================================")
    print("J.A.R.V.I.S. I2.2 V3 — REAL-WEB BENCHMARKS")
    print("==================================================\n")

    queries = [
        ("A. CURRENT TECHNICAL RESEARCH", "What is the latest stable React release and what changed?"),
        ("B. OFFICIAL DOCUMENTATION COMPARISON", "Compare FastAPI and Flask approaches to API development using their official documentation."),
        ("C. FACT CHECK", "Verify whether Python 3.14 has removed the GIL using primary sources."),
        ("D. NEWS SYNTHESIS", "What are the major AI developments today?"),
        ("E. CONFLICT TEST", "Compare Python 3.14 GIL removal vs retention across community sources.")
    ]

    for label, q in queries:
        print(f"--- BENCHMARK: {label} ---")
        print(f"Query: '{q}'")
        t0 = time.time()
        req = ResearchRequest(query=q, force_research=True)
        resp = await web_research_service.execute_research(req)
        elapsed = (time.time() - t0) * 1000

        print(f"Intent: {resp.intent.value}")
        print(f"Status: {resp.status.value}")
        print(f"Grounding Status: {resp.grounding_status.value}")
        print(f"Sources Discovered/Retrieved: {len(resp.sources)}")
        print(f"Evidence Items Selected: {len(resp.evidence_items)}")
        if resp.finding:
            print(f"Claims Generated: {len(resp.finding.claims)}")
            print(f"Conflicts Detected: {len(resp.finding.conflicts)}")
            if resp.finding.fact_check_detail:
                print(f"Fact-Check Verdict: {resp.finding.fact_check_detail.verdict.value}")
            print(f"Summary Output Snippet:\n{resp.finding.summary[:250]}...\n")
        print(f"Latency: {elapsed:.2f} ms\n")

if __name__ == "__main__":
    asyncio.run(run_benchmarks())
