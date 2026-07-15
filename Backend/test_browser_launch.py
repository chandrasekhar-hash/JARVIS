"""
Manual verification test for browser_open_url tool.

Tests:
1. SUCCESS PATH: "Open YouTube" should actually open the browser AND report success.
2. FAILURE PATH: A bogus protocol URL should fail and raise RuntimeError (not silently succeed).
"""
import sys
import asyncio

sys.path.insert(0, r'd:\JARVIS\Backend')
import tools
from tools.registry import registry


async def test_success_path():
    print("=" * 60)
    print("TEST 1: SUCCESS PATH -- Open YouTube")
    print("=" * 60)
    try:
        result = await registry.execute("browser_open_url", urls=["https://youtube.com"])
        print(f"  Result: {result}")
        if "Opened browser tabs for" in result:
            print("  [PASS] Tool reported success (browser was launched)")
        else:
            print(f"  [FAIL] Unexpected result: {result}")
    except Exception as e:
        print(f"  [FAIL] Tool raised exception on valid URL: {e}")


async def test_failure_path():
    print()
    print("=" * 60)
    print("TEST 2: FAILURE PATH -- Bogus protocol should raise error")
    print("=" * 60)
    try:
        result = await registry.execute("browser_open_url", urls=["invalidprotocol://not.a.real.thing"])
        # If we get here, the tool returned a string instead of raising
        if "Error" in result or "Failed" in result:
            print(f"  [SOFT FAIL] Tool returned error string instead of raising: {result}")
        else:
            print(f"  [FAIL] Tool reported success on bogus URL: {result}")
    except RuntimeError as e:
        print(f"  [PASS] Tool raised RuntimeError: {e}")
    except Exception as e:
        print(f"  [PASS] Tool raised {type(e).__name__}: {e}")


async def test_empty_urls():
    print()
    print("=" * 60)
    print("TEST 3: EDGE CASE -- Empty URL list")
    print("=" * 60)
    try:
        result = await registry.execute("browser_open_url", urls=[])
        print(f"  Result: {result}")
        if result == "Opened browser tabs for: ":
            print("  [INFO] Empty list returns empty success (acceptable)")
        else:
            print(f"  [INFO] Result: {result}")
    except Exception as e:
        print(f"  [INFO] Tool raised {type(e).__name__}: {e}")


async def main():
    await test_success_path()
    await test_failure_path()
    await test_empty_urls()
    print()
    print("=" * 60)
    print("ALL BROWSER LAUNCH VERIFICATION TESTS COMPLETE")
    print("=" * 60)
    print()
    print("MANUAL CHECK: Confirm that YouTube actually opened in your browser.")


if __name__ == "__main__":
    asyncio.run(main())
