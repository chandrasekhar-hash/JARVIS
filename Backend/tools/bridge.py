import asyncio
import json
import uuid
import contextvars
from typing import Any, Dict

# Context variable containing the asyncio.Queue for streaming SSE events back to the client
event_queue_var = contextvars.ContextVar("event_queue", default=None)

class BridgeManager:
    def __init__(self):
        # Maps request_id -> (asyncio.Event, result_dict)
        self._pending: Dict[str, tuple[asyncio.Event, Any]] = {}
        self._lock = asyncio.Lock()

    async def run_desktop_op(self, op: str, args: Dict[str, Any], timeout: float = 30.0) -> Any:
        req_id = str(uuid.uuid4())
        event = asyncio.Event()

        async with self._lock:
            self._pending[req_id] = (event, None)

        queue = event_queue_var.get()
        if not queue:
            raise RuntimeError(f"No active SSE queue found for request. Cannot execute bridge operation '{op}'.")

        payload = {
            "type": "bridge_request",
            "id": req_id,
            "op": op,
            "args": args
        }
        
        print(f"DEBUG_LOG: [Bridge] Registering request_id={req_id} for op='{op}'")
        # Enqueue the bridge request into the SSE queue
        await queue.put(f"data: {json.dumps(payload)}\n\n")

        try:
            # Wait for response callback
            await asyncio.wait_for(event.wait(), timeout=timeout)
            
            async with self._lock:
                _, result = self._pending.pop(req_id, (None, None))

            if result is None:
                raise RuntimeError(f"Bridge request {req_id} returned empty result.")

            if "error" in result and result["error"] is not None:
                raise RuntimeError(result["error"])

            return result.get("data")

        except asyncio.TimeoutError:
            async with self._lock:
                self._pending.pop(req_id, None)
            raise TimeoutError(f"Bridge request {req_id} timed out after {timeout}s waiting for client response.")
        except asyncio.CancelledError:
            async with self._lock:
                self._pending.pop(req_id, None)
            raise

    async def resolve_request(self, req_id: str, response: Dict[str, Any]) -> bool:
        async with self._lock:
            if req_id in self._pending:
                event, _ = self._pending[req_id]
                self._pending[req_id] = (event, response)
                event.set()
                print(f"DEBUG_LOG: [Bridge] Resolved request_id={req_id}")
                return True
        print(f"WARNING: [Bridge] Callback received for unknown or expired request_id={req_id}")
        return False

bridge_manager = BridgeManager()
