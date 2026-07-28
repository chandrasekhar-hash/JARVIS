from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Optional, List


class BaseRemoteInferenceProvider(ABC):
    """
    Abstract BaseRemoteInferenceProvider interface defining capability metadata
    and execution methods for Cloud LLM inference providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        pass

    @abstractmethod
    def supports_reasoning(self) -> bool:
        pass

    @abstractmethod
    def max_context_tokens(self) -> int:
        pass

    @abstractmethod
    async def execute_inference(self, prompt: str, system_instruction: Optional[str] = None, trace_id: str = "") -> Dict[str, Any]:
        pass

    @abstractmethod
    async def stream_inference(self, prompt: str, system_instruction: Optional[str] = None, trace_id: str = "") -> AsyncGenerator[str, None]:
        pass
