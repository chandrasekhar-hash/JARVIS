from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel

class ProviderMetadata(BaseModel):
    name: str
    supported_streaming: bool
    supports_tools: bool
    supports_vision: bool
    supports_audio: bool
    model_name: str
    supports_reasoning: bool = False
    supports_json: bool = False
    supports_long_context: bool = False
    supports_embeddings: bool = False
    average_latency: float = 2.0
    priority: int = 5

class AIToolCallFunction(BaseModel):
    name: str
    arguments: str # Standardized JSON string

class AIToolCall(BaseModel):
    id: str
    type: str = "function"
    function: AIToolCallFunction

class AIResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[AIToolCall]] = None
    finish_reason: str = "stop"
    provider_name: str
    model_name: str

class AIProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Returns metadata about the provider capabilities."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initializes the provider SDK/credentials."""
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 400
    ) -> AIResponse:
        """
        Sends a chat completion request to the provider.
        Returns a standardized AIResponse.
        """
        pass

    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 400
    ) -> AsyncGenerator[str, None]:
        """
        Streams response tokens back if supported.
        Yields raw string tokens.
        """
        pass
