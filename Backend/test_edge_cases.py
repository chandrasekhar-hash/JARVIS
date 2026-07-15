import sys
import os
import asyncio
import json

# Add current directory to path to ensure tools can be loaded
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.registry import registry
from tools.filesystem import validate_safe_path
from tools.apps import sanitize_app_name
import tools.router  # Import to access conversation_history
from tools.router import auto_summarize_history_if_needed
# Import tools module to trigger registrations
import tools

async def test_path_traversal():
    print("=== [TEST 1] Testing Path Traversal Defense ===")
    # 1. Normal safe path check
    safe_path = os.path.join(os.path.expanduser("~"), "Desktop", "notes.txt")
    try:
        resolved = validate_safe_path(safe_path)
        print(f"PASS: Permitted safe path resolved to: {resolved}")
    except PermissionError as e:
        print(f"FAIL: Safe path blocked: {str(e)}")

    # 2. Path traversal attack check
    unsafe_path = os.path.join(os.path.expanduser("~"), "Desktop", "..", "..", "Windows", "System32", "cmd.exe")
    try:
        validate_safe_path(unsafe_path, write_operation=True)
        print("FAIL: Directory traversal bypass succeeded!")
    except PermissionError as e:
        print(f"PASS: Blocked traversal path successfully: {str(e)}")

async def test_command_injection():
    print("\n=== [TEST 2] Testing Command Injection Defenses ===")
    insecure_payloads = [
        "calc.exe & notepad.exe",
        "calculator; taskkill /f /im explorer.exe",
        "Chrome | echo Hacked",
        "code; rm -rf /"
    ]
    for payload in insecure_payloads:
        sanitized = sanitize_app_name(payload)
        print(f"Dirty Command: '{payload}' -> Sanitized: '{sanitized}'")
        # Metacharacters must be completely stripped out
        if any(c in sanitized for c in ["&", ";", "|", "$", "`", "<", ">"]):
            print("FAIL: Sanitization did not strip metacharacter!")
        else:
            print("PASS: Sanitized command is clean.")

async def test_timeout_and_coercion():
    print("\n=== [TEST 3] Testing Parameter Coercion and Execution Timeouts ===")
    
    # Define a mock hanging tool
    @registry.register(
        name="test_hang_tool",
        description="A test tool that runs indefinitely to verify timeouts.",
        parameters={
            "type": "object",
            "properties": {
                "flag": {"type": "boolean"}
            }
        }
    )
    async def test_hang_tool(flag: bool):
        print(f"Mock tool executing: flag parameter coerced to {flag} (type: {type(flag)})")
        await asyncio.sleep(15.0)  # Exceeds the registry's 10.0s timeout limit
        return "Finished execution"

    # Test coercion: passing string "true" to a boolean parameter, and verify timeout
    print("Executing mock hang tool with string 'true' and 10s timeout limits...")
    try:
        # Await execution
        res = await registry.execute("test_hang_tool", flag="true", confirmed=True)
        print(f"FAIL: Tool completed despite hanging: {res}")
    except TimeoutError as e:
        print(f"PASS: Caught expected execution timeout error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

async def test_history_summarization():
    print("\n=== [TEST 4] Testing Conversation Auto-Summarization ===")
    
    # Clear and fill the history list with dummy conversation logs (16 messages)
    tools.router.conversation_history = []
    for i in range(8):
        tools.router.conversation_history.append({"role": "user", "content": f"Question {i}"})
        tools.router.conversation_history.append({"role": "assistant", "content": f"Answer {i}"})
        
    original_size = len(tools.router.conversation_history)
    print(f"Original conversation history size: {original_size} messages.")
    
    from config import GROQ_API_KEY
    if GROQ_API_KEY:
        print("Requesting live Groq auto-summarization on the oldest messages...")
        await auto_summarize_history_if_needed()
        new_size = len(tools.router.conversation_history)
        print(f"History size after compression check: {new_size} messages.")
        print(f"Current history memory state:")
        print(json.dumps(tools.router.conversation_history, indent=2))
        
        # Must be compressed
        if new_size < original_size:
            print("PASS: Successfully compressed history.")
        else:
            print("FAIL: History size remained unchanged.")
    else:
        print("Skipping live API summarization tests since GROQ_API_KEY is missing.")

async def main():
    await test_path_traversal()
    await test_command_injection()
    await test_timeout_and_coercion()
    await test_history_summarization()

if __name__ == "__main__":
    asyncio.run(main())
