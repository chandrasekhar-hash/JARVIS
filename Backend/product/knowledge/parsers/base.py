"""
JARVIS Product 1.6 - Base Parser Definition.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional
from ..interfaces import IParser


class BaseParser(IParser):
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name
