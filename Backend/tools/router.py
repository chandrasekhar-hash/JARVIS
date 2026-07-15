import json
import asyncio
import httpx
import time
from typing import AsyncGenerator
from tools.registry import registry
from tools.classifier import classify_intent
from config import GROQ_API_KEY
from tools.telemetry import telemetry_manager, log_structured, backend_log

# In-memory conversation history
# Structure: [{"role": "user"|"assistant"|"tool"|"system", "content": str, ...}]
conversation_history = []

# Persistent active state context
active_state = {
    "active_app": None,
    "active_browser_tab": None
}

def update_active_state(tool_name: str, arguments: dict):
    """Updates the global context state depending on the tool executed."""
    global active_state
    if tool_name in ["app_open", "app_switch"]:
        active_state["active_app"] = arguments.get("name")
    elif tool_name == "app_close":
        name = arguments.get("name", "").lower()
        if active_state["active_app"] and active_state["active_app"].lower() == name:
            active_state["active_app"] = None
    elif tool_name == "browser_open_url":
        active_state["active_app"] = "Browser"
        urls = arguments.get("urls", [])
        if urls:
            active_state["active_browser_tab"] = urls[0]
    elif tool_name == "browser_search":
        active_state["active_app"] = "Browser"
        active_state["active_browser_tab"] = f"Search: {arguments.get('query')}"

async def auto_summarize_history_if_needed():
    """Auto-summarizes oldest messages to manage memory growth and prevent context bloat."""
    global conversation_history
    if len(conversation_history) <= 15:
        return
        
    print(f"DEBUG_LOG: [Router] Conversation history length ({len(conversation_history)}) exceeds limit. Summarizing...")
    
    # Keep the system message or summaries, plus the last 5 turns
    to_summarize = conversation_history[:-5]
    to_keep = conversation_history[-5:]
    
    summary_prompt = (
        "Summarize the following chat history of an assistant and user. "
        "Describe actions performed and active context in exactly 1-2 sentences."
    )
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": json.dumps(to_summarize)}
        ],
        "temperature": 0.3,
        "max_tokens": 150
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15.0
            )
            if response.status_code == 200:
                summary = response.json()["choices"][0]["message"]["content"].strip()
                conversation_history = [
                    {"role": "system", "content": f"Summary of earlier conversation: {summary}"}
                ] + to_keep
                print(f"DEBUG_LOG: [Router] History summarized successfully: '{summary}'")
            else:
                # Fallback: slide history list
                conversation_history = conversation_history[6:]
    except Exception as e:
        print(f"DEBUG_LOG: [Router] Failed to summarize history: {str(e)}")
        conversation_history = conversation_history[6:]

async def handle_agent_chat(
    message: str,
    assistant_name: str,
    creator: str
) -> AsyncGenerator[str, None]:
    """
    Orchestrates the agent response flow.
    First runs the lightweight Intent Classifier. If it's a simple deterministic
    command, execution bypasses the LLM and runs the tool directly.
    Otherwise, invokes the Groq LLM tool calling agent loop.
    """
    global conversation_history, active_state
    
    # 1. Run the lightweight Intent Classifier first
    direct_match = classify_intent(message)
    if direct_match:
        tool_name = direct_match["tool_name"]
        tool_args = direct_match["arguments"]
        print(f"DEBUG_LOG: [Classifier] Direct execution match: {tool_name} with args {tool_args}")
        try:
            # Execute matching tool (requires await since execute is async)
            print(f"DEBUG_LOG: [Router/Classifier] Dispatching tool_name={tool_name!r} | tool_args={tool_args}")
            result = await registry.execute(tool_name, **tool_args)
            update_active_state(tool_name, tool_args)
        except Exception as e:
            result = f"Error executing direct command: {str(e)}"
            
        # Append to history
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": result})
        
        # Auto-summarize if needed
        await auto_summarize_history_if_needed()
        
        # Stream the deterministic response back
        for i in range(0, len(result), 5):
            yield result[i:i+5]
            await asyncio.sleep(0.01)
        return

    # 2. Complex Reasoning Command (LLM loop)
    conversation_history.append({"role": "user", "content": message})
    
    system_prompt = (
        f"You are {assistant_name}, a professional, calm, and confident AI assistant created by {creator}. "
        f"Provide extremely short, direct, and useful answers in natural Indian English. "
        f"Avoid any preamble, greetings, or repeating the user's question. Answer in 1-2 sentences at most, "
        f"unless the user explicitly asks for detailed explanations.\n"
        f"Identity boundaries:\n"
        f"- Your name is strictly: {assistant_name}.\n"
        f"- Your creator is strictly: {creator}.\n"
        f"- You have absolutely no connection to Tony Stark, Marvel, Iron Man, Stark Industries, or any other fictional universe or character.\n\n"
        f"You are an AI Agent with tools to control the host computer. Only use the tools explicitly provided in the tools schema list. "
        f"Do NOT call or reference any other tools (like brave_search, web_search, etc.). If a question can be answered from your "
        f"general knowledge (e.g. general questions like capitals, math, etc.), do NOT call any tools, just answer directly in text.\n\n"
        f"Current state:\n"
        f"- Active Application: {active_state['active_app'] or 'None'}\n"
        f"- Active Browser Tab: {active_state['active_browser_tab'] or 'None'}\n\n"
        f"Safety Rules:\n"
        f"1. For destructive actions (like file deletion, overwriting, shutdown, sleep, etc.), you MUST ask the user for confirmation "
        f"first in a conversational message. Do NOT call the tool with confirmed=True unless the user has explicitly confirmed "
        f"it in the chat history. If they have not confirmed it yet, call the tool with confirmed=False (or don't call it) and ask them.\n"
        f"2. Safe read-only or navigational actions can execute immediately."
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    tools = registry.get_tool_schemas()
    recent_history = conversation_history[-10:]
    current_messages = [{"role": "system", "content": system_prompt}] + recent_history

    # First call to check for tool calls (non-streaming)
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": current_messages,
        "temperature": 0.3,
        "max_tokens": 400
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient() as client:
        try:
            t_start = time.time()
            response = await client.post(
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
                yield err_msg
                return

            res_data = response.json()
            choice = res_data["choices"][0]
            message_data = choice["message"]
            tool_calls = message_data.get("tool_calls")

            iteration = 0
            MAX_TOOL_ITERATIONS = 5

            # Multi-turn tool execution loop
            while tool_calls and iteration < MAX_TOOL_ITERATIONS:
                iteration += 1
                print(f"DEBUG_LOG: [Router] Agent loop iteration {iteration}/{MAX_TOOL_ITERATIONS}")
                
                # 1. Deduplicate identical tool calls to prevent double execution
                seen_calls = set()
                unique_tool_calls = []
                for tc in tool_calls:
                    t_name = tc["function"]["name"]
                    t_args_str = tc["function"]["arguments"]
                    try:
                        t_args_dict = json.loads(t_args_str)
                        normalized = json.dumps(t_args_dict, sort_keys=True)
                    except Exception:
                        normalized = t_args_str
                        
                    key = (t_name, normalized)
                    if key not in seen_calls:
                        seen_calls.add(key)
                        unique_tool_calls.append(tc)
                    else:
                        print(f"DEBUG_LOG: [Router] Duplicate tool call for '{t_name}' deduplicated.")
                
                assistant_tool_msg = {
                    "role": "assistant",
                    "tool_calls": unique_tool_calls
                }
                conversation_history.append(assistant_tool_msg)
                
                # 2. Execute unique tools sequentially
                for tool_call in unique_tool_calls:
                    tc_id = tool_call["id"]
                    t_name = tool_call["function"]["name"]
                    t_args = json.loads(tool_call["function"]["arguments"])
                    
                    try:
                        # Execute (with locks and timeouts inside registry.execute)
                        print(f"DEBUG_LOG: [Router/LLM] Dispatching tool_name={t_name!r} | t_args={t_args}")
                        tool_result = await registry.execute(t_name, **t_args)
                        update_active_state(t_name, t_args)
                    except Exception as e:
                        tool_result = f"Error executing tool {t_name}: {str(e)}"
                        
                    tool_response_msg = {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": t_name,
                        "content": str(tool_result)
                    }
                    conversation_history.append(tool_response_msg)
                
                # 3. Call LLM again to determine next step
                recent_history = conversation_history[-10:]
                current_messages = [{"role": "system", "content": system_prompt}] + recent_history
                
                is_last_iter = (iteration == MAX_TOOL_ITERATIONS)
                
                payload_next = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": current_messages,
                    "temperature": 0.3,
                    "max_tokens": 400
                }
                if tools and not is_last_iter:
                    payload_next["tools"] = tools
                    payload_next["tool_choice"] = "auto"
                    
                t_start = time.time()
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload_next,
                    timeout=30.0
                )
                elapsed = time.time() - t_start
                telemetry_manager.record_latency("llm_latency", elapsed)
                telemetry_manager.increment_counter("llm_requests")
                if response.status_code != 200:
                    yield f"Error in agent iteration {iteration}: Status {response.status_code}"
                    return
                    
                res_data = response.json()
                choice = res_data["choices"][0]
                message_data = choice["message"]
                tool_calls = message_data.get("tool_calls")
                
                if not tool_calls or is_last_iter:
                    # Final response text achieved
                    content = message_data.get("content", "")
                    conversation_history.append({"role": "assistant", "content": content})
                    
                    # Stream response text
                    for i in range(0, len(content), 5):
                        yield content[i:i+5]
                        await asyncio.sleep(0.01)
                    break
            
            # If no tool calls in initial response, stream content directly
            if iteration == 0:
                content = message_data.get("content", "")
                conversation_history.append({"role": "assistant", "content": content})
                
                for i in range(0, len(content), 5):
                    yield content[i:i+5]
                    await asyncio.sleep(0.01)
            
            # Manage conversation history auto-summarization at the end of the turn
            await auto_summarize_history_if_needed()

        except Exception as e:
            yield f"Error in agent processing: {str(e)}"
