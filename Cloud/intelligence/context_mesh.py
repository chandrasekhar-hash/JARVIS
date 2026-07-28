import time
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("JARVIS_ContextMesh")


class ContextSnapshot(BaseModel):
    snapshot_id: str
    user_id: str
    device_id: str
    context_type: str  # e.g., "desktop_screen", "active_app", "user_intent", "mobile_location"
    version: int = 1
    confidence: float = 1.0
    data: Dict[str, Any]
    expires_at: float
    created_at: float = Field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class CrossDeviceContextProvider:
    """
    Formats multi-device context snapshots into unified system prompt context blocks for remote LLM inference.
    """

    @staticmethod
    def format_context_prompt_header(snapshots: List[ContextSnapshot]) -> str:
        valid_snapshots = [s for s in snapshots if not s.is_expired()]
        if not valid_snapshots:
            return ""

        header_lines = ["[CROSS-DEVICE ACTIVE CONTEXT]"]
        for s in valid_snapshots:
            line = (
                f"- Device '{s.device_id}' ({s.context_type}, v{s.version}, confidence {s.confidence:.2f}): "
                f"{json.dumps(s.data)}"
            )
            header_lines.append(line)
        header_lines.append("[END CROSS-DEVICE CONTEXT]\n")
        return "\n".join(header_lines)
