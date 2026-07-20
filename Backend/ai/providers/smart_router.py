import time
from typing import List, Dict, Any, Optional
from ai.providers.provider import AIProvider, AIResponse
from ai.providers.registry import provider_registry
import config
from tools.telemetry import log_structured, backend_log

class SmartRouter:
    def select_provider(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Determines the sorted list of compatible provider names based on request and capabilities.
        Outputs provider names in order of priority (descending) and latency (ascending).
        """
        # Determine capabilities required for the request
        req_tools = bool(tools)
        
        # Check if messages have vision/audio/long context
        req_vision = False
        req_audio = False
        total_chars = 0
        
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        t = item.get("type")
                        if t == "image_url":
                            req_vision = True
                        elif t == "input_audio":
                            req_audio = True
                        text_val = item.get("text")
                        if isinstance(text_val, str):
                            total_chars += len(text_val)

        req_long_context = total_chars > 15000
        
        # Filter registered providers by compatibility
        candidates = []
        registered = provider_registry.get_registered_providers()
        
        for name in registered.keys():
            try:
                p_class = registered[name]
                p_instance = provider_registry._instances.get(name) or p_class()
                meta = p_instance.metadata
                
                # Check compatibility
                if req_tools and not meta.supports_tools:
                    continue
                if req_vision and not meta.supports_vision:
                    continue
                if req_audio and not meta.supports_audio:
                    continue
                if req_long_context and not meta.supports_long_context:
                    continue
                    
                candidates.append((name, meta))
            except Exception as e:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[AI] Error reading metadata for provider '{name}': {str(e)}"
                )
                
        # Sort candidates: Priority desc, Latency asc
        candidates.sort(key=lambda x: (-x[1].priority, x[1].average_latency))
        
        sorted_names = [c[0] for c in candidates]
        
        # Log selection rationale
        reasons = []
        if req_tools: reasons.append("tools")
        if req_vision: reasons.append("vision")
        if req_audio: reasons.append("audio")
        if req_long_context: reasons.append("long_context")
        reasons_str = f"required: [{', '.join(reasons)}]" if reasons else "general text generation"
        
        log_structured(
            backend_log,
            "INFO",
            f"[AI] SmartRouter evaluated candidates: {sorted_names} for {reasons_str}"
        )
        
        return sorted_names

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 400
    ) -> AIResponse:
        routing_mode = getattr(config, "ROUTING_MODE", "manual").lower().strip()
        active_provider_name = provider_registry.active_provider_name
        
        # 1. Resolve preferred candidates list
        if routing_mode == "manual":
            # Manual mode: Only use active_provider_name
            candidates = [active_provider_name]
        else:
            # Auto or Fallback: Evaluate all compatible candidates
            candidates = self.select_provider(messages, tools)
            if not candidates:
                # Fallback to active if list empty
                candidates = [active_provider_name]
            elif routing_mode == "fallback" and active_provider_name in provider_registry.get_registered_providers():
                # In fallback mode, try preferred active_provider_name first, then follow list order
                if active_provider_name in candidates:
                    candidates.remove(active_provider_name)
                candidates.insert(0, active_provider_name)
                
        # 2. Try candidates sequentially (automatic failover)
        last_error = None
        for i, name in enumerate(candidates):
            try:
                provider = provider_registry.get_provider(name)
                log_structured(
                    backend_log,
                    "INFO",
                    f"[AI] Routing completion request to provider '{name}' (mode: {routing_mode}, candidate {i+1}/{len(candidates)})"
                )
                
                t_start = time.time()
                response = await provider.chat_completion(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                elapsed = time.time() - t_start
                
                log_structured(
                    backend_log,
                    "INFO",
                    f"[AI] Provider '{name}' completed successfully in {elapsed:.3f}s"
                )
                return response
                
            except Exception as e:
                last_error = e
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[AI] Provider '{name}' failed during request: {str(e)}"
                )
                # If routing_mode is not 'fallback' and not 'auto', do NOT failover, raise immediately
                if routing_mode not in ["fallback", "auto"]:
                    break
                    
        # If all candidates fail, raise final exception
        err_msg = f"All compatible providers failed. Last error: {str(last_error)}"
        log_structured(backend_log, "ERROR", f"[AI] SmartRouter failure: {err_msg}")
        raise RuntimeError(err_msg)

smart_router = SmartRouter()
