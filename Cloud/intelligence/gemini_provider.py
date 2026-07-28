import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, Optional
from Cloud.intelligence.base_provider import BaseRemoteInferenceProvider

logger = logging.getLogger("JARVIS_GeminiProvider")


class GeminiRemoteProvider(BaseRemoteInferenceProvider):
    @property
    def provider_name(self) -> str:
        return "gemini"

    def supports_streaming(self) -> bool:
        return True

    def supports_tools(self) -> bool:
        return True

    def supports_reasoning(self) -> bool:
        return True

    def max_context_tokens(self) -> int:
        return 1048576

    async def execute_inference(self, prompt: str, system_instruction: Optional[str] = None, trace_id: str = "") -> Dict[str, Any]:
        logger.info(f"[{trace_id}] GeminiRemoteProvider executing remote inference prompt (len: {len(prompt)})")
        await asyncio.sleep(0.05)
        return {
            "provider": self.provider_name,
            "text": f"Gemini Cloud Response for: '{prompt[:40]}...'",
            "model": "gemini-2.0-flash-exp",
            "tokens_used": len(prompt.split()) + 30,
            "trace_id": trace_id
        }

    async def stream_inference(self, prompt: str, system_instruction: Optional[str] = None, trace_id: str = "") -> AsyncGenerator[str, None]:
        tokens = [f"Gemini ", "Cloud ", "Streamed ", "Response ", "for ", f"'{prompt[:30]}...'"]
        for token in tokens:
            await asyncio.sleep(0.02)
            yield token
