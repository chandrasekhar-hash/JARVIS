"""
Automated and manual verification test suite for the dynamic Application Resolver.
"""
import sys
import os
import asyncio

sys.path.insert(0, r'd:\JARVIS\Backend')
import tools
from tools.registry import registry
from tools.app_discovery import AppCacheManager
from tools.app_resolver import resolve_application, MATCH_SINGLE, MATCH_MULTIPLE, MATCH_NONE

async def test_matching_capabilities():
    print("=" * 60)
    print("1. TESTING RESOLUTION ALGORITHMS")
    print("=" * 60)
    cache_manager = AppCacheManager()
    app_list = cache_manager.load_or_refresh()
    print(f"Total apps in index: {len(app_list)}")

    test_queries = [
        # Test Case, Expected matching type or sample matching app
        ("notepad", "Notepad"),
        ("calculator", "Calculator"),
        ("chrome", "Google Chrome"),
        ("code", "VS Code / Visual Studio"),
        ("vs code", "Visual Studio Code"),
        ("pycharm", "PyCharm"),
        ("spotify", "Spotify"),
        ("discord", "Discord"),
        ("capcut", "CapCut"),
        ("cursor", "Cursor"),
        ("bogusappname123", "None")
    ]

    for query, description in test_queries:
        status, matches = resolve_application(query, app_list)
        print(f"Query: '{query}' ({description})")
        print(f"  Result Status: {status}")
        if status == MATCH_SINGLE:
            print(f"  Resolved to: '{matches[0].name}' (Path: {matches[0].path})")
        elif status == MATCH_MULTIPLE:
            print(f"  Ambiguity detected. Matches: {[m.name for m in matches]}")
        else:
            print("  No matches found.")
        print()

async def test_tool_app_open():
    print("=" * 60)
    print("2. TESTING app_open TOOL EXECUTION")
    print("=" * 60)
    
    # Test a known single match
    print("Query: 'app_open' with name='notepad'")
    try:
        res = await registry.execute("app_open", name="notepad")
        print(f"  Result: {res}")
    except Exception as e:
        print(f"  Error: {e}")
    print()

    # Test ambiguity handling
    print("Query: 'app_open' with name='code'")
    try:
        res = await registry.execute("app_open", name="code")
        print(f"  Result: {res}")
    except Exception as e:
        print(f"  Error: {e}")
    print()

    # Test bogus app handling
    print("Query: 'app_open' with name='bogusappname123'")
    try:
        res = await registry.execute("app_open", name="bogusappname123")
        print(f"  Result: {res}")
    except Exception as e:
        print(f"  Error: {e}")
    print()

async def test_refresh_index_tool():
    print("=" * 60)
    print("3. TESTING app_refresh_index TOOL")
    print("=" * 60)
    try:
        res = await registry.execute("app_refresh_index")
        print(f"  Result: {res}")
    except Exception as e:
        print(f"  Error: {e}")
    print()

async def main():
    await test_matching_capabilities()
    await test_tool_app_open()
    await test_refresh_index_tool()

if __name__ == "__main__":
    asyncio.run(main())
