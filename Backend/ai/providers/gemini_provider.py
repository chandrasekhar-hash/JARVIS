import os
import time
import json
import uuid
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from ai.providers.provider import AIProvider, AIResponse, AIToolCall, AIToolCallFunction, ProviderMetadata
import config
from tools.telemetry import telemetry_manager, log_structured, backend_log

class GeminiProvider(AIProvider):
    def __init__(self):
        self.api_key = None
        self.model_name = None
        self.initialized = False

    @property
    def metadata(self) -> ProviderMetadata:
        self._ensure_config()
        return ProviderMetadata(
            name="Gemini",
            supported_streaming=True,
            supports_tools=True,
            supports_vision=True,
            supports_audio=True,
            model_name=self.model_name,
            supports_reasoning=True,
            supports_json=True,
            supports_long_context=True,
            supports_embeddings=True,
            average_latency=1.5,
            priority=8
        )

    def _ensure_config(self) -> None:
        if not self.api_key or not self.model_name:
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY") or getattr(config, "GEMINI_API_KEY", None)
            self.model_name = getattr(config, "GEMINI_MODEL", "gemini-1.5-flash")

    def initialize(self) -> None:
        self._ensure_config()
        if not self.api_key:
            # Reload dotenv in case keys were written
            from config import frontend_env_path
            from dotenv import load_dotenv
            if frontend_env_path.exists():
                load_dotenv(dotenv_path=frontend_env_path)
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY") or getattr(config, "GEMINI_API_KEY", None)
            
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing from configuration.")
            
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        self.initialized = True
        log_structured(backend_log, "INFO", "[AI] Gemini Provider initialized")

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 400
    ) -> AIResponse:
        self._ensure_config()
        if not self.initialized:
            self.initialize()

        import google.generativeai as genai

        log_structured(backend_log, "INFO", "[AI] Provider request started")
        t_start = time.time()
        
        try:
            system_instruction = None
            system_messages = [msg["content"] for msg in messages if msg["role"] == "system"]
            if system_messages:
                system_instruction = "\n".join(system_messages)
                
            gemini_tools = []
            if tools:
                for tool_schema in tools:
                    func_schema = tool_schema["function"]
                    parameters = dict(func_schema.get("parameters", {}))
                    parameters = self._clean_schema(parameters)
                    
                    fd = genai.types.FunctionDeclaration(
                        name=func_schema["name"],
                        description=func_schema["description"],
                        parameters=parameters
                    )
                    gemini_tools.append(fd)
                    
            gemini_contents = self._convert_messages(messages)
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                tools=gemini_tools if gemini_tools else None,
                system_instruction=system_instruction
            )
            
            loop = asyncio.get_event_loop()
            
            def call_gemini():
                generation_config = genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
                return model.generate_content(
                    contents=gemini_contents,
                    generation_config=generation_config
                )
                
            response = await loop.run_in_executor(None, call_gemini)
            
            elapsed = time.time() - t_start
            telemetry_manager.record_latency("llm_latency", elapsed)
            telemetry_manager.increment_counter("llm_requests")
            
            converted_response = self._convert_response(response)
            log_structured(backend_log, "INFO", "[AI] Provider response completed")
            return converted_response
            
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[AI] Gemini Provider request failed: {str(e)}")
            raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 400
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError("Streaming is handled by simulated chunks in current architecture.")

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        import google.generativeai as genai
        gemini_contents = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                continue
                
            parts = []
            if "content" in msg and msg["content"] is not None:
                if role == "tool":
                    parts.append({
                        "function_response": {
                            "name": msg["name"],
                            "response": {"result": msg["content"]}
                        }
                    })
                else:
                    parts.append({"text": msg["content"]})
                    
            if "tool_calls" in msg and msg["tool_calls"] is not None:
                for tc in msg["tool_calls"]:
                    parts.append({
                        "function_call": {
                            "name": tc["function"]["name"],
                            "args": json.loads(tc["function"]["arguments"])
                        }
                    })
                    
            if parts:
                gemini_role = "user"
                if role == "assistant":
                    gemini_role = "model"
                elif role == "tool":
                    gemini_role = "function"
                    
                gemini_contents.append({
                    "role": gemini_role,
                    "parts": parts
                })
        return gemini_contents

    def _convert_response(self, response: Any) -> AIResponse:
        if not response.candidates:
            raise RuntimeError(f"Gemini API returned no candidates. Prompt feedback: {response.prompt_feedback}")
            
        candidate = response.candidates[0]
        content = candidate.content
        
        tool_calls = []
        text_content = ""
        
        if content and content.parts:
            for part in content.parts:
                if part.function_call:
                    fc = part.function_call
                    tool_calls.append(
                        AIToolCall(
                            id=f"call_{uuid.uuid4().hex[:8]}",
                            type="function",
                            function=AIToolCallFunction(
                                name=fc.name,
                                arguments=json.dumps(dict(fc.args))
                            )
                        )
                    )
                elif part.text:
                    text_content += part.text
                    
        return AIResponse(
            content=text_content if text_content else None,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason="tool_calls" if tool_calls else "stop",
            provider_name="Gemini",
            model_name=self.model_name
        )

    def _clean_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively removes unsupported schema fields like 'default' and 'additionalProperties' for Gemini."""
        if not isinstance(schema, dict):
            return schema
            
        cleaned = {}
        for k, v in schema.items():
            if k in ["default", "$schema", "additionalProperties"]:
                continue
            if isinstance(v, dict):
                cleaned[k] = self._clean_schema(v)
            elif isinstance(v, list):
                cleaned[k] = [self._clean_schema(item) if isinstance(item, dict) else item for item in v]
            else:
                cleaned[k] = v
        return cleaned
