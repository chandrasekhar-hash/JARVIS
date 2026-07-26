from typing import Protocol, Optional, Dict, Any


class BaseCacheProvider(Protocol):
    def get(self, key: str) -> Optional[Any]:
        ...

    def set(self, key: str, value: Any, ttl_sec: Optional[float] = None) -> bool:
        ...

    def delete(self, key: str) -> bool:
        ...

    def clear(self) -> bool:
        ...

    def exists(self, key: str) -> bool:
        ...

    def ttl(self, key: str) -> Optional[float]:
        ...

    def statistics(self) -> Dict[str, Any]:
        ...
