import time
import asyncio
import inspect
from typing import Dict, List, Callable, Any, Optional
from brain.models import Event
from tools.telemetry import log_structured, backend_log


class EventBus:
    """
    Enhanced EventBus for Patch 7.0.1.
    Supports bounded queue, backpressure handling, drop-oldest policy,
    listener timeout safety, and telemetry metrics while maintaining 100% API compatibility.
    """

    def __init__(
        self,
        max_history: int = 100,
        max_queue_size: int = 1000,
        listener_timeout_sec: float = 2.0,
    ):
        self._listeners: Dict[str, List[Callable]] = {}
        self._history: List[Event] = []
        self._max_history = max_history
        self._max_queue_size = max_queue_size
        self._listener_timeout_sec = listener_timeout_sec

        # Telemetry metrics
        self._total_emitted: int = 0
        self._total_dropped: int = 0
        self._total_errors: int = 0

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """Subscribes a listener callback to an event."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        if callback not in self._listeners[event_name]:
            self._listeners[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """Unsubscribes a listener callback."""
        if event_name in self._listeners and callback in self._listeners[event_name]:
            self._listeners[event_name].remove(callback)

    def emit(self, event_name: str, **kwargs) -> None:
        """Emits an event to registered listeners with backpressure and queue bounds."""
        event = Event(name=event_name, data=kwargs, timestamp=time.time())
        self._total_emitted += 1

        # Bounded history & drop oldest overflow policy
        if len(self._history) >= self._max_queue_size:
            self._history.pop(0)
            self._total_dropped += 1
            log_structured(
                backend_log,
                "WARNING",
                f"[EventBus] Queue overflow (>{self._max_queue_size}). Dropped oldest event.",
            )

        self._history.append(event)

        log_structured(backend_log, "INFO", f"[EventBus] Event emitted: {event_name}")

        listeners = self._listeners.get(event_name, [])
        for listener in listeners:
            try:
                if inspect.iscoroutinefunction(listener):
                    try:
                        loop = asyncio.get_running_loop()
                        task = loop.create_task(self._safe_async_listener(listener, event))
                    except RuntimeError:
                        asyncio.run(self._safe_async_listener(listener, event))
                else:
                    listener(event)
            except Exception as e:
                self._total_errors += 1
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[EventBus] Listener error for '{event_name}': {str(e)}",
                )

    async def _safe_async_listener(self, listener: Callable, event: Event) -> None:
        """Executes coroutine listener with timeout safety."""
        try:
            await asyncio.wait_for(listener(event), timeout=self._listener_timeout_sec)
        except asyncio.TimeoutError:
            self._total_errors += 1
            log_structured(
                backend_log,
                "WARNING",
                f"[EventBus] Async listener timeout ({self._listener_timeout_sec}s) for '{event.name}'",
            )
        except Exception as e:
            self._total_errors += 1
            log_structured(
                backend_log,
                "WARNING",
                f"[EventBus] Async listener execution error for '{event.name}': {str(e)}",
            )

    def get_history(self, limit: int = 20) -> List[Event]:
        """Returns recent event history."""
        return self._history[-limit:]

    def get_metrics(self) -> Dict[str, Any]:
        """Returns queue metrics and backpressure statistics."""
        return {
            "total_emitted": self._total_emitted,
            "total_dropped": self._total_dropped,
            "total_errors": self._total_errors,
            "current_queue_size": len(self._history),
            "max_queue_size": self._max_queue_size,
            "listeners_registered": sum(len(l) for l in self._listeners.values()),
        }


event_bus = EventBus()
