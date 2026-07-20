import sys
import os
import asyncio

# Add current directory to path to ensure tools can be loaded
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.router import handle_agent_chat

async def run_query(query: str):
    print(f"\nQuery: '{query}'")
    print("-" * 50)
    
    response_tokens = []
    async for token in handle_agent_chat(query, "J.A.R.V.I.S.", "Chandrasekhar"):
        response_tokens.append(token)
        print(token, end="", flush=True)
    
    full_response = "".join(response_tokens)
    print(f"\n\n--> Final Consolidated Response: {full_response}\n")

async def main():
    from config import ACTIVE_PROVIDER, GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY, CEREBRAS_API_KEY
    if ACTIVE_PROVIDER == "gemini":
        active_key = GEMINI_API_KEY
    elif ACTIVE_PROVIDER == "openrouter":
        active_key = OPENROUTER_API_KEY
    elif ACTIVE_PROVIDER == "cerebras":
        active_key = CEREBRAS_API_KEY
    else:
        active_key = GROQ_API_KEY
        
    if not active_key:
        print(f"WARNING: API key for active provider '{ACTIVE_PROVIDER}' is not configured. Live LLM tests will fail, but direct commands will still work.")
    
    print("=== Starting Agent Routing Tests ===")
    
    # 1. Test Direct Execution Intent Match
    print("\n[TEST 1] Testing Deterministic Command (bypasses LLM, runs tool directly)")
    await run_query("scroll down")
    
    # 2. Test Complex reasoning/conversational (calls active provider LLM)
    if active_key:
        print(f"\n[TEST 2] Testing Complex Query (Requires {ACTIVE_PROVIDER.upper()} LLM reasoning)")
        await run_query("What is the capital of France? Answer in one short sentence.")
        
        # 3. Test Safety Confirmation logic
        print("\n[TEST 3] Testing Safety/Confirmation flow for destructive action")
        await run_query("Delete the file fake_temp_file_123.txt")
    else:
        print(f"\nSkipping live LLM tests because API key for active provider '{ACTIVE_PROVIDER}' is missing.")

if __name__ == "__main__":
    asyncio.run(main())
    print("=== Agent Routing Tests Complete ===")
