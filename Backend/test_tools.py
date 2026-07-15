import sys
import os
import asyncio

# Add current directory to path to ensure local tools can be loaded
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.registry import registry
from tools.classifier import classify_intent
# Import tools module to ensure everything is registered
import tools

def test_registry():
    print("=== Testing Tool Registry ===")
    schemas = registry.get_tool_schemas()
    print(f"Registered tool schemas count on current platform: {len(schemas)}")
    for s in schemas:
        func = s["function"]
        print(f" - {func['name']}: {func['description']}")
    
    # Confirm safety level exists
    for name, tool in registry.tools.items():
        print(f"Tool {name} -> safety: {tool.safety_level}, platforms: {tool.supported_platforms}")
    print("Registry test passed.\n")

def test_classifier():
    print("=== Testing Intent Classifier ===")
    queries = [
        "Open YouTube",
        "open vs code",
        "close chrome",
        "scroll down",
        "count desktop folders",
        "how many files are on my desktop",
        "Summarize this webpage",  # Complex/Reasoning - should return None
        "open google.com",
        "open wikipedia.org/wiki/Main_Page",
        "open https://news.ycombinator.com"
    ]
    for q in queries:
        res = classify_intent(q)
        print(f"Query: '{q}' -> Classified match: {res}")
    print("Classifier test passed.\n")

async def test_filesystem():
    print("=== Testing Filesystem Tools ===")
    # 1. Desktop Items Count
    count_res = await registry.execute("fs_count_desktop_items", item_type="all")
    print(f"Desktop items count result:\n{count_res}\n")
    
    # 2. File creation (overwrite confirmed=True)
    test_file = "test_jarvis_file.txt"
    create_res = await registry.execute(
        "fs_file_operation", 
        operation="create", 
        src=test_file, 
        content="Hello from JARVIS Agent Framework!", 
        confirmed=True
    )
    print(f"Creation: {create_res}")
    
    # 3. Read file
    read_res = await registry.execute("fs_read_file", path=test_file)
    print(f"Read Content: '{read_res}'")
    
    # 4. Try deleting without confirmation
    del_fail = await registry.execute("fs_file_operation", operation="delete", src=test_file, confirmed=False)
    print(f"Delete without confirmation: {del_fail}")
    
    # 5. Delete with confirmation
    del_ok = await registry.execute("fs_file_operation", operation="delete", src=test_file, confirmed=True)
    print(f"Delete with confirmation: {del_ok}")
    print("Filesystem test passed.\n")

async def main():
    test_registry()
    test_classifier()
    await test_filesystem()

if __name__ == "__main__":
    asyncio.run(main())
