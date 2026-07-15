import os
import sys
import asyncio
import json

# Ensure backend imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import health_endpoint, ready_endpoint, metrics_endpoint
from tools.startup import verify_startup
from tools.telemetry import telemetry_manager, task_watchdog

async def run_observability_tests():
    print("=== [TEST 1] Testing Startup Diagnostics ===")
    try:
        verify_startup()
        print("PASS: Startup diagnostics completed successfully.")
    except Exception as e:
        print(f"FAIL: Startup diagnostics failed: {str(e)}")

    print("\n=== [TEST 2] Testing Health Endpoint ===")
    health = health_endpoint()
    print(f"Health check response: {health}")
    if health == {"status": "healthy"}:
        print("PASS: /health returned healthy status.")
    else:
        print("FAIL: /health returned unexpected result.")

    print("\n=== [TEST 3] Testing Metrics Endpoint ===")
    # Record some mock metrics first
    telemetry_manager.record_latency("llm_latency", 0.452)
    telemetry_manager.record_latency("tts_latency", 0.128)
    telemetry_manager.record_latency("tool_latency", 0.050)
    telemetry_manager.increment_counter("llm_requests")
    telemetry_manager.increment_counter("tts_requests")
    
    metrics = metrics_endpoint()
    print(f"Metrics keys: {list(metrics.keys())}")
    print(f"Metrics RAM usage: {metrics['system']['ram_mb']:.2f} MB")
    print(f"Metrics Active Tasks: {metrics['active_tasks']}")
    
    if "llm_latency" in metrics and "system" in metrics:
        print("PASS: /metrics successfully captured system and rolling latencies.")
    else:
        print("FAIL: /metrics missing expected categories.")

    print("\n=== [TEST 4] Testing Ready Endpoint ===")
    ready_response = await ready_endpoint()
    # Read response body and code
    status_code = ready_response.status_code
    body = json.loads(ready_response.body.decode("utf-8"))
    print(f"Ready endpoint status: {status_code}")
    print(f"Ready endpoint details: {json.dumps(body, indent=2)}")
    
    if status_code in [200, 503]:
        print("PASS: /ready endpoint returned correctly (diagnostics parsed).")
    else:
        print("FAIL: /ready returned unexpected status code.")

if __name__ == "__main__":
    asyncio.run(run_observability_tests())
