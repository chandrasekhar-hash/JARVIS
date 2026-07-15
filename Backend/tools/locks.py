import asyncio
from typing import Dict

# Global lock to prevent multiple destructive operations from executing simultaneously
destructive_lock = asyncio.Lock()

# Thread/coroutine locks per tool name to prevent duplicate concurrent executions
_tool_locks: Dict[str, asyncio.Lock] = {}
_locks_creation_lock = asyncio.Lock()

async def get_tool_lock(tool_name: str) -> asyncio.Lock:
    """Returns or creates a lock for a specific tool to ensure sequential execution."""
    async with _locks_creation_lock:
        if tool_name not in _tool_locks:
            _tool_locks[tool_name] = asyncio.Lock()
        return _tool_locks[tool_name]
