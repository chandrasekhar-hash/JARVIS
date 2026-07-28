import time
import logging
from typing import Dict, Any, List, Set, Optional, Tuple

logger = logging.getLogger("JARVIS_Cloud_CRDT")


class LWWRegister:
    """
    Last-Write-Wins Register for Settings & Preferences.
    Scalar register keeping highest timestamp value.
    """

    def __init__(self, value: Any = None, timestamp: float = 0.0, device_id: str = ""):
        self.value = value
        self.timestamp = timestamp
        self.device_id = device_id

    def update(self, value: Any, timestamp: float, device_id: str) -> bool:
        if timestamp > self.timestamp or (timestamp == self.timestamp and device_id > self.device_id):
            self.value = value
            self.timestamp = timestamp
            self.device_id = device_id
            return True
        return False

    def merge(self, other: "LWWRegister") -> bool:
        return self.update(other.value, other.timestamp, other.device_id)

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "timestamp": self.timestamp, "device_id": self.device_id}


class ORSetElement:
    def __init__(self, element_id: str, value: Any, tag: str, timestamp: float):
        self.element_id = element_id
        self.value = value
        self.tag = tag
        self.timestamp = timestamp


class ORSet:
    """
    Observed-Remove Set for Tasks & Plugin states.
    Allows concurrent additions and removals without state corruption.
    """

    def __init__(self):
        self.add_set: Dict[str, ORSetElement] = {}  # tag -> ORSetElement
        self.remove_set: Set[str] = set()  # set of removed tags

    def add(self, element_id: str, value: Any, tag: str = None, timestamp: float = None) -> str:
        tag = tag or f"tag_{time.time()}_{element_id}"
        ts = timestamp or time.time()
        self.add_set[tag] = ORSetElement(element_id, value, tag, ts)
        return tag

    def remove(self, tag: str):
        self.remove_set.add(tag)

    def read(self) -> List[Any]:
        items = []
        for tag, elem in self.add_set.items():
            if tag not in self.remove_set:
                items.append(elem.value)
        return items

    def merge(self, other: "ORSet"):
        # Merge addition sets
        for tag, elem in other.add_set.items():
            if tag not in self.add_set:
                self.add_set[tag] = elem

        # Union remove sets
        self.remove_set.update(other.remove_set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adds": {k: {"element_id": v.element_id, "value": v.value, "tag": v.tag, "timestamp": v.timestamp} for k, v in self.add_set.items()},
            "removes": list(self.remove_set)
        }


class LWWMap:
    """
    Last-Write-Wins Map for Memory & Conversation Metadata.
    Key-Value map where each key is an independent LWWRegister.
    """

    def __init__(self):
        self.entries: Dict[str, LWWRegister] = {}

    def set(self, key: str, value: Any, timestamp: float = None, device_id: str = "") -> bool:
        ts = timestamp or time.time()
        if key not in self.entries:
            self.entries[key] = LWWRegister(value, ts, device_id)
            return True
        return self.entries[key].update(value, ts, device_id)

    def get(self, key: str) -> Any:
        reg = self.entries.get(key)
        return reg.value if reg else None

    def read(self) -> Dict[str, Any]:
        return {k: reg.value for k, reg in self.entries.items()}

    def merge(self, other: "LWWMap") -> int:
        conflicts_resolved = 0
        for key, other_reg in other.entries.items():
            if key not in self.entries:
                self.entries[key] = LWWRegister(other_reg.value, other_reg.timestamp, other_reg.device_id)
                conflicts_resolved += 1
            else:
                updated = self.entries[key].merge(other_reg)
                if updated:
                    conflicts_resolved += 1
        return conflicts_resolved

    def to_dict(self) -> Dict[str, Any]:
        return {k: reg.to_dict() for k, reg in self.entries.items()}


class CRDTEngine:
    """
    Deterministic CRDT Engine orchestrating Settings, Memory, Tasks, Preferences, and Conversation Metadata.
    """

    def __init__(self):
        self.settings = LWWMap()
        self.preferences = LWWMap()
        self.tasks = ORSet()
        self.memory = LWWMap()
        self.conversation_metadata = LWWMap()
        self.conflicts_count = 0

    def merge_settings(self, incoming_dict: Dict[str, Any], timestamp: float, device_id: str) -> int:
        other_map = LWWMap()
        for k, v in incoming_dict.items():
            other_map.set(k, v, timestamp, device_id)
        resolved = self.settings.merge(other_map)
        self.conflicts_count += resolved
        return resolved

    def merge_memory(self, incoming_dict: Dict[str, Any], timestamp: float, device_id: str) -> int:
        other_map = LWWMap()
        for k, v in incoming_dict.items():
            other_map.set(k, v, timestamp, device_id)
        resolved = self.memory.merge(other_map)
        self.conflicts_count += resolved
        return resolved

    def merge_tasks(self, incoming_or_set_dict: Dict[str, Any]):
        other = ORSet()
        adds = incoming_or_set_dict.get("adds", {})
        for tag, item in adds.items():
            other.add(item["element_id"], item["value"], tag, item["timestamp"])
        other.remove_set = set(incoming_or_set_dict.get("removes", []))
        self.tasks.merge(other)

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "settings": self.settings.read(),
            "preferences": self.preferences.read(),
            "tasks": self.tasks.read(),
            "memory": self.memory.read(),
            "conversation_metadata": self.conversation_metadata.read(),
            "conflicts_count": self.conflicts_count
        }


crdt_engine = CRDTEngine()
