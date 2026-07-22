import time
import asyncio
import inspect
from typing import Dict, List, Callable, Any
from brain.models import Event
from tools.telemetry import log_structured, backend_log

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._history: List[Event] = []
        self._max_history = 100

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
        """Emits an event to registered listeners."""
        event = Event(name=event_name, data=kwargs, timestamp=time.time())
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        log_structured(backend_log, "INFO", f"[EventBus] Event emitted: {event_name}")

        listeners = self._listeners.get(event_name, [])
        for listener in listeners:
            try:
                if inspect.iscoroutinefunction(listener):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(listener(event))
                    except RuntimeError:
                        asyncio.run(listener(event))
                else:
                    listener(event)
            except Exception as e:
                log_structured(backend_log, "WARNING", f"[EventBus] Listener error for '{event_name}': {str(e)}")

    def get_history(self, limit: int = 20) -> List[Event]:
        """Returns recent event history."""
        return self._history[-limit:]

event_bus = EventBus()
