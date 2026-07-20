from typing import List, Dict, Any, Optional
from ai.providers.provider import AIResponse
from ai.providers.smart_router import smart_router

class AIRouter:
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 400
    ) -> AIResponse:
        # Delegate completion handling to the smart router
        return await smart_router.chat_completion(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens
        )

ai_router = AIRouter()
