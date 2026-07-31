"""
JARVIS Product 1.7 - Base Trigger Listener Interface.
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, Any
from ..models import Workflow


class BaseTriggerListener(ABC):
    def __init__(self, name: str):
        self.name = name
        self.callback: Callable[[Workflow, Dict[str, Any]], None] = None

    def set_callback(self, callback: Callable[[Workflow, Dict[str, Any]], None]) -> None:
        self.callback = callback

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass
