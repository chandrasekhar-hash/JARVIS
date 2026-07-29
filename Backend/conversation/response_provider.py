"""
Response Provider Abstractions & Implementations for J.A.R.V.I.S. Phase V1.3 Conversation Engine.
Provides Local, OpenAI, Groq, Gemini, and Mock response generation backends with ResponseProviderFactory.
"""
from abc import ABC, abstractmethod
from typing import Optional
from conversation.models import ConversationTurn, ConversationSession, ConversationState, IntentType


class IResponseProvider(ABC):
    """Abstract interface for conversation response generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns provider identifier name."""
        pass

    @abstractmethod
    async def generate_response(
        self,
        turn: ConversationTurn,
        session: ConversationSession,
        state: ConversationState,
    ) -> str:
        """Generates assistant response for the conversation turn."""
        pass


class LocalResponseProvider(IResponseProvider):
    """Direct local rule-based response provider."""

    @property
    def name(self) -> str:
        return "LocalResponseProvider"

    async def generate_response(
        self,
        turn: ConversationTurn,
        session: ConversationSession,
        state: ConversationState,
    ) -> str:
        text = turn.user_text.strip()
        text_lower = text.lower()

        if "hello" in text_lower or "hi" in text_lower or "hey" in text_lower:
            return "Hello! I am J.A.R.V.I.S. How may I assist you today?"
        elif "status" in text_lower or "system" in text_lower:
            return "All J.A.R.V.I.S. core systems are online and operating at nominal parameters."
        elif "time" in text_lower:
            return "System time is synchronized and operational."
        elif "who are you" in text_lower:
            return "I am J.A.R.V.I.S., your autonomous AI assistant."

        # Default rule-based acknowledgment
        active_topic = state.active_topic.topic_name if state.active_topic else "general"
        return f"I have processed your request regarding '{active_topic}': '{text}'."


class OpenAIResponseProvider(IResponseProvider):
    """OpenAI GPT response provider abstraction."""

    @property
    def name(self) -> str:
        return "OpenAIResponseProvider"

    async def generate_response(
        self,
        turn: ConversationTurn,
        session: ConversationSession,
        state: ConversationState,
    ) -> str:
        return f"OpenAI Response: Processed turn '{turn.user_text}'."


class GroqResponseProvider(IResponseProvider):
    """Groq Llama-3 response provider abstraction."""

    @property
    def name(self) -> str:
        return "GroqResponseProvider"

    async def generate_response(
        self,
        turn: ConversationTurn,
        session: ConversationSession,
        state: ConversationState,
    ) -> str:
        return f"Groq Response: Processed turn '{turn.user_text}'."


class GeminiResponseProvider(IResponseProvider):
    """Google Gemini response provider abstraction."""

    @property
    def name(self) -> str:
        return "GeminiResponseProvider"

    async def generate_response(
        self,
        turn: ConversationTurn,
        session: ConversationSession,
        state: ConversationState,
    ) -> str:
        return f"Gemini Response: Processed turn '{turn.user_text}'."


class MockResponseProvider(IResponseProvider):
    """Mock response provider for testing and deterministic validation."""

    @property
    def name(self) -> str:
        return "MockResponseProvider"

    async def generate_response(
        self,
        turn: ConversationTurn,
        session: ConversationSession,
        state: ConversationState,
    ) -> str:
        text = turn.user_text.strip()
        if turn.intent and turn.intent.intent == IntentType.QUESTION:
            return f"Answer to query '{text}': All parameters are validated."
        elif turn.intent and turn.intent.intent == IntentType.COMMAND:
            return f"Executed command '{text}' successfully."
        elif turn.intent and turn.intent.intent == IntentType.FOLLOW_UP:
            resolved_ref = list(state.resolved_references.values())[0] if state.resolved_references else "previous context"
            return f"Following up on {resolved_ref}: Request processed."
        return f"Processed turn '{text}' under active session '{session.session_id}'."


class ResponseProviderFactory:
    """Factory creating IResponseProvider instances based on configuration/name."""

    @staticmethod
    def create_provider(provider_name: Optional[str] = "local") -> IResponseProvider:
        name = (provider_name or "local").lower().strip()
        if name == "openai":
            return OpenAIResponseProvider()
        elif name == "groq":
            return GroqResponseProvider()
        elif name == "gemini":
            return GeminiResponseProvider()
        elif name == "mock":
            return MockResponseProvider()
        return LocalResponseProvider()
