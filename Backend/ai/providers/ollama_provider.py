import os
import time
import json
import uuid
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
from ai.providers.provider import AIProvider, AIResponse, AIToolCall, AIToolCallFunction, ProviderMetadata
import config
from tools.telemetry import telemetry_manager, log_structured, backend_log

class OllamaProvider(AIProvider):
    def __init__(self):
        self.base_url = None
        self.model_name = None
        self.client = None
        self._measured_latency = 0.2
        self.initialized = False

    @property
    def metadata(self) -> ProviderMetadata:
        self._ensure_config()
        return ProviderMetadata(
            name="Ollama",
            supported_streaming=True,
            supports_tools=True,
            supports_vision=False,
            supports_audio=False,
            model_name=self.model_name,
            supports_reasoning=True,
            supports_json=True,
            supports_long_context=True,
            supports_embeddings=False,
            average_latency=self._measured_latency,
            priority=7
        )

    def _ensure_config(self) -> None:
        if not self.base_url or not self.model_name:
            self.base_url = getattr(config, "OLLAMA_BASE_URL", "http://localhost:11434")
            self.model_name = getattr(config, "OLLAMA_MODEL", "qwen3:8b")

    def initialize(self) -> None:
        self._ensure_config()
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
        self.health_check()
        self.initialized = True
        log_structured(backend_log, "INFO", f"[AI] Ollama Provider initialized (model: {self.model_name})")

    def health_check(self) -> bool:
        """
        Performs a health check by pinging /api/tags, checking if Ollama server
        is reachable and if the configured model is installed. Also measures dynamic latency.
        """
        self._ensure_config()
        t0 = time.time()
        try:
            with httpx.Client(base_url=self.base_url, timeout=5.0) as sync_client:
                res = sync_client.get("/api/tags")
                elapsed = time.time() - t0
                self._measured_latency = round(elapsed, 3)
                
                if res.status_code != 200:
                    log_structured(backend_log, "WARNING", f"[AI] Ollama health check returned status {res.status_code}")
                    return False
                    
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                
                # Check if model exists (exact match or tag match)
                model_exists = any(self.model_name == m or m.startswith(f"{self.model_name}:") for m in models)
                if not model_exists and models:
                    log_structured(
                        backend_log,
                        "WARNING",
                        f"[AI] Configured Ollama model '{self.model_name}' not found in local models: {models}."
                    )
                return True
        except Exception as e:
            self._measured_latency = 5.0
            log_structured(backend_log, "WARNING", f"[AI] Ollama server health check failed: {str(e)}")
            return False

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

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        if tools:
            payload["tools"] = tools

        log_structured(backend_log, "INFO", "[AI] Ollama Provider request started")
        t_start = time.time()
        try:
            response = await self.client.post("/api/chat", json=payload, timeout=60.0)
            elapsed = time.time() - t_start
            self._measured_latency = round(elapsed, 3)
            telemetry_manager.record_latency("llm_latency", elapsed)
            telemetry_manager.increment_counter("llm_requests")

            if response.status_code != 200:
                err_msg = f"Ollama API error: Status {response.status_code}. Details: {response.text}"
                log_structured(backend_log, "ERROR", f"[AI] Ollama Provider request failed: {err_msg}")
                raise RuntimeError(err_msg)

            res_data = response.json()
            message_data = res_data.get("message", {})
            
            standardized_tool_calls = None
            raw_tool_calls = message_data.get("tool_calls")
            if raw_tool_calls:
                standardized_tool_calls = []
                for tc in raw_tool_calls:
                    func = tc.get("function", {})
                    args = func.get("arguments", {})
                    args_str = json.dumps(args) if isinstance(args, dict) else str(args)
                    standardized_tool_calls.append(
                        AIToolCall(
                            id=tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                            type="function",
                            function=AIToolCallFunction(
                                name=func.get("name", ""),
                                arguments=args_str
                            )
                        )
                    )

            log_structured(backend_log, "INFO", "[AI] Ollama Provider response completed")
            return AIResponse(
                content=message_data.get("content"),
                tool_calls=standardized_tool_calls,
                finish_reason=res_data.get("done_reason", "stop"),
                provider_name="Ollama",
                model_name=self.model_name
            )
        except httpx.ConnectError as e:
            err_msg = f"Ollama server unreachable at {self.base_url}: {str(e)}"
            log_structured(backend_log, "ERROR", f"[AI] {err_msg}")
            raise RuntimeError(err_msg) from e
        except httpx.TimeoutException as e:
            err_msg = f"Ollama request timed out: {str(e)}"
            log_structured(backend_log, "ERROR", f"[AI] {err_msg}")
            raise RuntimeError(err_msg) from e
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[AI] Ollama Provider exception: {str(e)}")
            raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 400
    ) -> AsyncGenerator[str, None]:
        self._ensure_config()
        if not self.client:
            self.initialize()

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            async with self.client.stream("POST", "/api/chat", json=payload, timeout=60.0) as response:
                if response.status_code != 200:
                    err_text = await response.aread()
                    raise RuntimeError(f"Ollama streaming API error: Status {response.status_code}. Details: {err_text.decode('utf-8')}")

                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        msg = chunk.get("message", {})
                        token = msg.get("content", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[AI] Ollama streaming error: {str(e)}")
            raise
