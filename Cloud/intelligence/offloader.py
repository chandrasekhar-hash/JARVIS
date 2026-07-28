import uuid
import logging
from typing import Dict, Any, AsyncGenerator, Optional, List
from Cloud.intelligence.base_provider import BaseRemoteInferenceProvider
from Cloud.intelligence.groq_provider import GroqRemoteProvider
from Cloud.intelligence.gemini_provider import GeminiRemoteProvider
from Cloud.intelligence.openrouter_provider import OpenRouterRemoteProvider
from Cloud.intelligence.circuit_breaker import CircuitBreaker

logger = logging.getLogger("JARVIS_RemoteInferenceOffloader")


class RemoteInferenceOffloader:
    """
    Remote LLM Inference Offloader managing multi-provider routing (Groq, Gemini, OpenRouter),
    circuit breaker failure isolation, streaming responses, and ContextVar trace_id injection.
    """

    def __init__(self):
        self.providers: Dict[str, BaseRemoteInferenceProvider] = {
            "groq": GroqRemoteProvider(),
            "gemini": GeminiRemoteProvider(),
            "openrouter": OpenRouterRemoteProvider()
        }
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            name: CircuitBreaker(provider_name=name) for name in self.providers.keys()
        }
        self.provider_priority: List[str] = ["groq", "gemini", "openrouter"]

    def _select_available_provider(self, preferred_provider: Optional[str] = None) -> Optional[str]:
        if preferred_provider and preferred_provider in self.providers:
            if self.circuit_breakers[preferred_provider].allow_request():
                return preferred_provider

        for p_name in self.provider_priority:
            if self.circuit_breakers[p_name].allow_request():
                return p_name
        return None

    async def execute_remote_inference(
        self,
        prompt: str,
        preferred_provider: Optional[str] = None,
        system_instruction: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        trace_id = trace_id or f"trc_inf_{uuid.uuid4().hex[:12]}"
        provider_name = self._select_available_provider(preferred_provider)

        if not provider_name:
            msg = "All remote inference LLM providers are currently tripped (CircuitBreakers OPEN)."
            logger.error(f"[{trace_id}] {msg}")
            raise RuntimeError(msg)

        provider = self.providers[provider_name]
        breaker = self.circuit_breakers[provider_name]

        try:
            res = await provider.execute_inference(prompt, system_instruction, trace_id=trace_id)
            breaker.record_success()
            return res
        except Exception as e:
            logger.error(f"[{trace_id}] Failure on provider '{provider_name}': {e}")
            breaker.record_failure()
            # Attempt failover provider
            failover_name = self._select_available_provider()
            if failover_name and failover_name != provider_name:
                logger.info(f"[{trace_id}] Failing over to provider '{failover_name}'...")
                f_provider = self.providers[failover_name]
                f_res = await f_provider.execute_inference(prompt, system_instruction, trace_id=trace_id)
                self.circuit_breakers[failover_name].record_success()
                return f_res
            raise e

    async def stream_remote_inference(
        self,
        prompt: str,
        preferred_provider: Optional[str] = None,
        system_instruction: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        trace_id = trace_id or f"trc_stm_{uuid.uuid4().hex[:12]}"
        provider_name = self._select_available_provider(preferred_provider)

        if not provider_name:
            raise RuntimeError("All remote inference LLM providers are currently unavailable.")

        provider = self.providers[provider_name]
        breaker = self.circuit_breakers[provider_name]

        try:
            async for token in provider.stream_inference(prompt, system_instruction, trace_id=trace_id):
                yield token
            breaker.record_success()
        except Exception as e:
            logger.error(f"[{trace_id}] Streaming failure on provider '{provider_name}': {e}")
            breaker.record_failure()
            raise e

    def get_circuit_status(self) -> Dict[str, Any]:
        return {name: cb.get_status() for name, cb in self.circuit_breakers.items()}


remote_offloader = RemoteInferenceOffloader()
