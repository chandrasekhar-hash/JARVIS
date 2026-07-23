import time
import uuid
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class RawObservation(BaseModel):
    """
    Normalized observation format capturing raw perception streams from diverse sources
    before ingestion, validation, classification, and storage.
    """
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "user_action"  # conversation | vision | tool_execution | desktop_event | file | user_action
    title: str = ""
    content: str = ""
    timestamp: float = Field(default_factory=time.time)
    payload: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ObservationCapture:
    """
    Normalizes diverse perception payloads into standardized RawObservation instances.
    """

    @staticmethod
    def from_conversation(user_message: str, assistant_response: str = "", metadata: Optional[Dict[str, Any]] = None) -> RawObservation:
        content_str = f"User: {user_message.strip()}"
        if assistant_response.strip():
            content_str += f"\nAssistant: {assistant_response.strip()}"
            
        return RawObservation(
            source="conversation",
            title=f"Conversation: {user_message[:30]}...",
            content=content_str,
            payload={"user_message": user_message, "assistant_response": assistant_response},
            tags=["conversation", "chat"],
            metadata=metadata or {}
        )

    @staticmethod
    def from_vision(visual_context: Dict[str, Any]) -> RawObservation:
        active_app = visual_context.get("active_app", {})
        headline = visual_context.get("headline", "Screen Observation")
        full_text = visual_context.get("full_text", "")
        
        content_str = f"Active App: {active_app.get('app_name', 'Unknown')} ({active_app.get('window_title', '')})\nHeadline: {headline}"
        if full_text:
            content_str += f"\nOCR Text: {full_text[:200]}"

        return RawObservation(
            source="vision",
            title=f"Vision: {headline[:30]}",
            content=content_str,
            payload=visual_context,
            tags=["vision", "screen", active_app.get("category", "desktop")],
            metadata={"workflow": visual_context.get("workflow", "")}
        )

    @staticmethod
    def from_tool_execution(tool_name: str, args: Dict[str, Any], result: Any) -> RawObservation:
        content_str = f"Executed Tool '{tool_name}' with args {args}.\nResult: {str(result)[:200]}"
        return RawObservation(
            source="tool_execution",
            title=f"Tool Execution: {tool_name}",
            content=content_str,
            payload={"tool_name": tool_name, "args": args, "result": str(result)},
            tags=["tool", tool_name, "execution"],
            metadata={"safety_level": "executed"}
        )

    @staticmethod
    def from_desktop_event(event_type: str, details: Dict[str, Any]) -> RawObservation:
        content_str = f"Desktop Event '{event_type}': {details}"
        return RawObservation(
            source="desktop_event",
            title=f"Desktop Event: {event_type}",
            content=content_str,
            payload=details,
            tags=["desktop", event_type],
            metadata={}
        )

    @staticmethod
    def from_file(file_path: str, summary_or_content: str) -> RawObservation:
        return RawObservation(
            source="file",
            title=f"File Context: {file_path}",
            content=f"File Path: {file_path}\nContent Summary: {summary_or_content[:300]}",
            payload={"file_path": file_path, "summary": summary_or_content},
            tags=["file", "workspace"],
            metadata={"path": file_path}
        )

    @staticmethod
    def from_raw_payload(payload: Dict[str, Any]) -> RawObservation:
        return RawObservation(
            source=payload.get("source", "user_action"),
            title=payload.get("title", "Raw Observation"),
            content=payload.get("content", str(payload)),
            payload=payload,
            tags=payload.get("tags", []),
            metadata=payload.get("metadata", {})
        )
