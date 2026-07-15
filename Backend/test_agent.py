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
    from config import GROQ_API_KEY
    if not GROQ_API_KEY:
        print("WARNING: GROQ_API_KEY is not configured on the backend. Live LLM tests will fail, but direct commands will still work.")
    
    print("=== Starting Agent Routing Tests ===")
    
    # 1. Test Direct Execution Intent Match
    print("\n[TEST 1] Testing Deterministic Command (bypasses LLM, runs tool directly)")
    await run_query("scroll down")
    
    # 2. Test Complex reasoning/conversational (calls Groq LLM)
    if GROQ_API_KEY:
        print("\n[TEST 2] Testing Complex Query (Requires LLM reasoning)")
        await run_query("What is the capital of France? Answer in one short sentence.")
        
        # 3. Test Safety Confirmation logic
        print("\n[TEST 3] Testing Safety/Confirmation flow for destructive action")
        await run_query("Delete the file fake_temp_file_123.txt")
    else:
        print("\nSkipping live LLM tests because GROQ_API_KEY is missing.")

if __name__ == "__main__":
    asyncio.run(main())
    print("=== Agent Routing Tests Complete ===")
