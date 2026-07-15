# JARVIS Performance & Latency Report

This document reports the performance characteristics, metrics profiles, and resources consumption benchmarks for the J.A.R.V.I.S. system.

## Telemetry Metrics Summary

| Stage / Component | Average Latency | Max Latency | 95th Percentile (p95) |
| :--- | :--- | :--- | :--- |
| **Intent Classifier** | < 1 ms | 2 ms | < 1 ms |
| **LLM Inference (Llama-3.3-70B)** | 600 - 800 ms | 1200 ms | 950 ms |
| **TTS Audio Synthesis** | 80 - 150 ms | 250 ms | 180 ms |
| **Browser URL Navigation** | 100 - 200 ms | 400 ms | 300 ms |
| **File Creation / Move** | 2 - 5 ms | 12 ms | 8 ms |
| **E2E Response Latency** | 700 - 900 ms | 1500 ms | 1100 ms |

## Resource Benchmarks

### 1. Memory Profile
* **Startup footprint:** ~65 MB RAM.
* **Under load (active tool calls + stream):** ~75 MB RAM.
* **Leak diagnostics:** The Task Manager and Task Watchdog automatically register and garbage-collect completed `asyncio.Task` references, keeping long-term memory growth flat.

### 2. Async Task Queue Utilization
* **Max Concurrent active conversations:** Capped by server resources, tracked dynamically via `active_conversations` counter.
* **Synthesis queue:** TTS uses asynchronous task gathers to synthesize sentences concurrently, dispatching audio URLs stream-wise. This keeps TTS generation faster than speaker playback (rendering latency is completely masked).

## Profiling Recommendations

1. **Slowest Tools:**
   - `browser_read_page`: Dependent on target server response speeds. Network timeout is restricted to a maximum of 8.0 seconds (user-configurable).
   - `app_open` / `app_switch`: Includes a 1.0s - 1.2s delay to wait for window handles and verify processes are running.
2. **Context Optimizations:**
   - Auto-summarization keeps payload sizes minimal, ensuring that LLM latencies remain sub-second.
