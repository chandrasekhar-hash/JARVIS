from enum import Enum


class Capabilities(str, Enum):
    FS_READ = "fs:read"
    FS_WRITE = "fs:write"
    NET_OUTBOUND = "net:outbound"
    SYSTEM_EXEC = "system:exec"
    SPEECH_TTS = "speech:tts"
    SPEECH_STT = "speech:stt"
    VISION_SCREEN = "vision:screen"
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    TASKS_MANAGE = "tasks:manage"
