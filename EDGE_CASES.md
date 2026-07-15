# JARVIS Edge Case Handling & Stability Documentation

This document logs critical edge cases, vulnerabilities, and potential failure points handled in the JARVIS architecture, explaining root causes, implemented mitigations, and verification.

| Scenario | Root Cause | Fix / Prevention | Verification Method |
| :--- | :--- | :--- | :--- |
| **Tool Execution Hanging** | Synchronous tools run on the main loop and can block indefinitely if resources or sockets hang. | Wrapped tool calls in a 10s `asyncio.wait_for` timeout. Sync tools run in a threadpool executor. | [test_edge_cases.py](file:///d:/JARVIS/Backend/test_edge_cases.py#L42) mock hang tool timeout pass. |
| **Directory Traversal** | Path parameters resolving outside allowed home/workspace directory scopes. | Created a `validate_safe_path` validator that checks inputs against permitted folders. | [test_edge_cases.py](file:///d:/JARVIS/Backend/test_edge_cases.py#L14) traversal attempts raise `PermissionError`. |
| **Command Injection** | Passing raw user application names directly to a subprocess executing with shell=True. | Sanitized inputs to strip metacharacters and spawn binaries using list parameter arrays. | [test_edge_cases.py](file:///d:/JARVIS/Backend/test_edge_cases.py#L29) strips `&`, `;`, `\|` commands. |
| **TTS Audio Queue Deadlock** | Network or load failures on a synthesized TTS URL caused the audio queue to halt. | Added `audio.onerror` in [Terminal.jsx](file:///d:/JARVIS/frontend/src/component/Terminal.jsx) to automatically skip failed chunks. | Simulated load error on the client; segment is skipped, next audio plays immediately. |
| **Barge-in Voice Feedback** | Microphone captures speaker output, triggering voice commands or barge-in loops. | Implemented substring similarity filters on interim SpeechRecognition results. | Spoke simultaneously; user speech interrupts active speaker, assistant feedback ignored. |
| **Background Task Leaks** | SSE connection closed by client while backend is still executing tools or TTS. | Monitored `asyncio.CancelledError` in FastAPI and cancelled the producer task. | Aborted connection manually; logs confirm task cancellation and cleanup. |
| **History Context Bloat** | Chat history memory list grows past the model's capacity, causing slower/failed calls. | Implemented a sliding history buffer that auto-summarizes old turns in the background. | [test_edge_cases.py](file:///d:/JARVIS/Backend/test_edge_cases.py#L60) slides 16 turns down to 6 turns. |

## Known Limitations

1. **Anti-Scraping / Cloudflare Protection:** Reading pages via `browser_read_page` uses standard HTTP fetches. If websites use advanced scraper protections, the tool will return a permission check warning.
2. **PyAutoGUI Coordinate Resolution:** If browser windows are minimized, coordinates for clicks or scrolling might hit desktop areas. Windows should be focused first via `app_switch`.
3. **Speech Recognition Accuracy:** Native Web Speech API is dependent on Chrome/Edge platform models. Pronunciations or high noise environments can lead to command classification mismatches.
