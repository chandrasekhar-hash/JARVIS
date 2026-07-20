import httpx
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from ai.providers.provider import AIProvider, AIResponse, AIToolCall, AIToolCallFunction, ProviderMetadata
import config
from tools.telemetry import telemetry_manager, log_structured, backend_log

class GroqProvider(AIProvider):
    def __init__(self):
        self.api_key = None
        self.model_name = None
        self.client = None

    @property
    def metadata(self) -> ProviderMetadata:
        self._ensure_config()
        return ProviderMetadata(
            name="Groq",
            supported_streaming=True,
            supports_tools=True,
            supports_vision=False,
            supports_audio=False,
            model_name=self.model_name,
            supports_reasoning=True,
            supports_json=True,
            supports_long_context=True,
            supports_embeddings=False,
            average_latency=0.8,
            priority=10
        )

    def _ensure_config(self) -> None:
        if not self.api_key or not self.model_name:
            self.api_key = getattr(config, "GROQ_API_KEY", None)
            self.model_name = getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile")

    def initialize(self) -> None:
        self._ensure_config()
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing from configuration.")
        self.client = httpx.AsyncClient()
        log_structured(backend_log, "INFO", "[AI] Groq Provider initialized")

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 400
    ) -> AIResponse:
        self._ensure_config()
        if not self.client:
            self.initialize()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        log_structured(backend_log, "INFO", "[AI] Provider request started")
        t_start = time.time()
        try:
            response = await self.client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            elapsed = time.time() - t_start
            telemetry_manager.record_latency("llm_latency", elapsed)
            telemetry_manager.increment_counter("llm_requests")
            
            if response.status_code != 200:
                err_msg = f"Groq API error: Status {response.status_code}. Details: {response.text}"
                log_structured(backend_log, "ERROR", f"[AI] Groq Provider request failed: {err_msg}")
                raise RuntimeError(err_msg)
                
            log_structured(backend_log, "INFO", "[AI] Provider response completed")
            
            res_data = response.json()
            choice = res_data["choices"][0]
            message_data = choice["message"]
            
            standardized_tool_calls = None
            if "tool_calls" in message_data and message_data["tool_calls"]:
                standardized_tool_calls = [
                    AIToolCall(
                        id=tc["id"],
                        type="function",
                        function=AIToolCallFunction(
                            name=tc["function"]["name"],
                            arguments=tc["function"]["arguments"]
                        )
                    )
                    for tc in message_data["tool_calls"]
                ]

            return AIResponse(
                content=message_data.get("content"),
                tool_calls=standardized_tool_calls,
                finish_reason=choice.get("finish_reason", "stop"),
                provider_name="Groq",
                model_name=self.model_name
            )
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[AI] Groq Provider request exception: {str(e)}")
            raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 400
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError("Streaming is handled by simulated chunks in current architecture.")
