import time
import hashlib
from typing import List, Dict, Any, Optional
from intelligence.vision.camera.models import CameraFrame, SessionStatus, VisionSessionState
from tools.telemetry import log_structured, backend_log

MAX_KEYFRAMES_PER_SESSION = 5
DEFAULT_SESSION_TIMEOUT_SECONDS = 300  # 5 minutes auto-timeout

class VisionSession:
    """
    Vision Session Abstraction (V7).
    Maintains temporary, ephemeral in-memory state:
    - Session lifecycle & touch timestamp
    - In-memory rolling keyframe buffer (max 5 keyframes)
    - Active conversational focus target (pronoun resolution "this", "here")
    - Conversational context turns
    - Scene summary
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = time.time()
        self.last_accessed_at = time.time()
        self.status = SessionStatus.ACTIVE
        self.keyframes: List[CameraFrame] = []
        self.frame_counter = 0
        self.active_focus: Optional[str] = None
        self.scene_summary: Optional[str] = None
        self.conversational_context: List[Dict[str, str]] = []

    def touch(self):
        self.last_accessed_at = time.time()

    def add_keyframe(self, data: bytes, width: int = 1280, height: int = 720) -> CameraFrame:
        self.touch()
        self.frame_counter += 1
        hash_code = hashlib.sha256(data).hexdigest()[:16]

        frame = CameraFrame(
            frame_index=self.frame_counter,
            timestamp=time.time(),
            data=data,
            width=width,
            height=height,
            hash_code=hash_code
        )

        self.keyframes.append(frame)
        # Keep rolling buffer of max 5 keyframes
        if len(self.keyframes) > MAX_KEYFRAMES_PER_SESSION:
            self.keyframes.pop(0)

        return frame

    def get_latest_keyframe(self) -> Optional[CameraFrame]:
        return self.keyframes[-1] if self.keyframes else None

    def get_recent_keyframe_items(self) -> List[Any]:
        """
        Returns VisionImageItem format for multi-image reasoning across buffered keyframes.
        """
        from intelligence.vision.models import VisionImageItem
        items = []
        for idx, kf in enumerate(self.keyframes, start=1):
            items.append(VisionImageItem(
                filename=f"Keyframe_{idx}.jpg",
                content_type="image/jpeg",
                data=kf.data,
                size=len(kf.data)
            ))
        return items

    def update_focus(self, focus_name: Optional[str]):
        if focus_name:
            self.active_focus = focus_name.strip()
            self.touch()

    def add_turn(self, role: str, text: str):
        self.conversational_context.append({"role": role, "content": text[:1000]})
        if len(self.conversational_context) > 10:
            self.conversational_context.pop(0)
        self.touch()

    def clear(self):
        self.keyframes.clear()
        self.conversational_context.clear()
        self.active_focus = None
        self.scene_summary = None
        self.status = SessionStatus.TERMINATED


class VisionSessionManager:
    """
    Vision Session Manager (V7).
    Manages active ephemeral sessions, auto-timeout expiration, and safe memory purging.
    No database persistence.
    """

    def __init__(self):
        self.sessions: Dict[str, VisionSession] = {}

    def get_or_create_session(self, session_id: str) -> VisionSession:
        self.cleanup_expired_sessions()
        if session_id not in self.sessions:
            log_structured(backend_log, "INFO", f"[VisionSessionManager] Creating new ephemeral session '{session_id}'...")
            self.sessions[session_id] = VisionSession(session_id)
        else:
            self.sessions[session_id].touch()

        return self.sessions[session_id]

    def get_session(self, session_id: str) -> Optional[VisionSession]:
        self.cleanup_expired_sessions()
        session = self.sessions.get(session_id)
        if session:
            session.touch()
        return session

    def purge_session(self, session_id: str):
        if session_id in self.sessions:
            log_structured(backend_log, "INFO", f"[VisionSessionManager] Purging session '{session_id}' memory...")
            self.sessions[session_id].clear()
            del self.sessions[session_id]

    def cleanup_expired_sessions(self, timeout_seconds: int = DEFAULT_SESSION_TIMEOUT_SECONDS):
        now = time.time()
        expired_ids = [
            sid for sid, s in self.sessions.items()
            if (now - s.last_accessed_at) > timeout_seconds
        ]
        for sid in expired_ids:
            log_structured(backend_log, "INFO", f"[VisionSessionManager] Auto-purging expired session '{sid}'...")
            self.sessions[sid].clear()
            del self.sessions[sid]

# Singleton Instance
session_manager = VisionSessionManager()
