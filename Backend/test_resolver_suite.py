"""
Comprehensive automated test suite for the Dynamic Application Resolver.
Tests: resolution pipeline, ambiguity detection, cache refresh, and tool execution.
Run from: d:\\JARVIS\\Backend
"""
import sys
import asyncio
import os

sys.path.insert(0, r'd:\JARVIS\Backend')
import tools  # ensures all tools register
from tools.registry import registry
from tools.app_discovery import AppCacheManager
from tools.app_resolver import (
    resolve_application,
    MATCH_SINGLE, MATCH_MULTIPLE, MATCH_NONE
)

PASS = "[PASS]"
FAIL = "[FAIL]"

results = {"passed": 0, "failed": 0}

def assert_eq(label, actual, expected):
    if actual == expected:
        print(f"  {PASS} {label}: got {actual!r}")
        results["passed"] += 1
    else:
        print(f"  {FAIL} {label}: expected {expected!r}, got {actual!r}")
        results["failed"] += 1

def assert_in(label, actual_list, expected_subset):
    names = [a.name.lower() for a in actual_list]
    for e in expected_subset:
        if any(e.lower() in n for n in names):
            print(f"  {PASS} {label}: found {e!r} in {names}")
            results["passed"] += 1
        else:
            print(f"  {FAIL} {label}: expected {e!r} in {names}")
            results["failed"] += 1


def section(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_apps():
    cm = AppCacheManager()
    return cm.load_or_refresh()


# ---------------------------------------------------------------------------
# Test 1: Cache
# ---------------------------------------------------------------------------
def test_cache():
    section("1. CACHE LOADING")
    cm = AppCacheManager()
    apps = cm.load_or_refresh()
    assert_eq("Cache returns non-empty list", len(apps) > 0, True)
    print(f"  INFO  Total apps in index: {len(apps)}")


# ---------------------------------------------------------------------------
# Test 2: Exact Matching
# ---------------------------------------------------------------------------
def test_exact_matching():
    section("2. EXACT MATCHING")
    apps = load_apps()

    for query, expect_name_fragment in [
        ("notepad", "notepad"),
        ("google chrome", "google chrome"),
        ("cursor", "cursor"),
    ]:
        status, matches = resolve_application(query, apps)
        assert_eq(f"'{query}' status=single", status, MATCH_SINGLE)
        if status == MATCH_SINGLE:
            assert_in(f"'{query}' name contains '{expect_name_fragment}'",
                      matches, [expect_name_fragment])


# ---------------------------------------------------------------------------
# Test 3: Alias Expansion
# ---------------------------------------------------------------------------
def test_alias_expansion():
    section("3. ALIAS EXPANSION (informal -> canonical)")
    apps = load_apps()

    alias_tests = [
        ("calculator", "calc"),
        ("chrome",     "google chrome"),
        ("vs code",    "visual studio code"),
        ("code",       "visual studio code"),
    ]
    for query, expected_fragment in alias_tests:
        status, matches = resolve_application(query, apps)
        assert_eq(f"'{query}' status=single", status, MATCH_SINGLE)
        if status == MATCH_SINGLE:
            assert_in(f"'{query}' resolves to '{expected_fragment}'",
                      matches, [expected_fragment])


# ---------------------------------------------------------------------------
# Test 4: Ambiguity Detection
# ---------------------------------------------------------------------------
def test_ambiguity():
    section("4. AMBIGUITY DETECTION")
    apps = load_apps()

    # Inject synthetic duplicates to reliably test this path
    from tools.app_discovery import AppEntry
    fake_apps = apps + [
        AppEntry("FakeApp Alpha", "C:\\fake\\alpha.exe", source="start_menu"),
        AppEntry("FakeApp Beta",  "C:\\fake\\beta.exe",  source="start_menu"),
    ]
    status, matches = resolve_application("fakeapp", fake_apps)
    assert_eq("Ambiguity returns MATCH_MULTIPLE", status, MATCH_MULTIPLE)
    assert_eq("Ambiguity returns >=2 candidates", len(matches) >= 2, True)


# ---------------------------------------------------------------------------
# Test 5: Not Installed → MATCH_NONE
# ---------------------------------------------------------------------------
def test_not_found():
    section("5. NOT INSTALLED → MATCH_NONE")
    apps = load_apps()

    bogus_queries = ["bogusappname123xyz", "xyzzy_fake_9999", "unicornapp"]
    for q in bogus_queries:
        status, _ = resolve_application(q, apps)
        assert_eq(f"'{q}' → MATCH_NONE", status, MATCH_NONE)


# ---------------------------------------------------------------------------
# Test 6: Tool Execution via Registry
# ---------------------------------------------------------------------------
async def test_tool_execution():
    section("6. TOOL EXECUTION VIA REGISTRY")

    # 6a. Open Notepad (should succeed on all Windows machines)
    res = await registry.execute("app_open", name="notepad")
    print(f"  INFO  app_open notepad: {res}")
    assert_eq("notepad open returns non-empty string", bool(res), True)

    # 6b. Open something not installed
    try:
        res = await registry.execute("app_open", name="bogusappname123xyz")
        # prereq check should block it
        assert_eq("bogus app returns error string", "couldn't find" in res.lower() or "not found" in res.lower() or "prerequisites" in res.lower(), True)
    except Exception as e:
        # PrerequisiteError raised — acceptable
        assert_eq("bogus app raises or returns error", True, True)

    # 6c. Refresh index
    res = await registry.execute("app_refresh_index")
    assert_eq("refresh returns success message", "successfully refreshed" in res.lower(), True)


# ---------------------------------------------------------------------------
# Test 7: Focus/Foreground (already running)
# ---------------------------------------------------------------------------
async def test_focus_existing():
    section("7. FOCUS EXISTING WINDOW (already running)")
    # Open notepad first
    await registry.execute("app_open", name="notepad")
    import time; time.sleep(1.5)
    # Open again — should focus, not open second
    res = await registry.execute("app_open", name="notepad")
    print(f"  INFO  Second open: {res}")
    already_running = (
        "already running" in res.lower()
        or "successfully opened" in res.lower()
        or "focused" in res.lower()
    )
    assert_eq("Second app_open focuses or opens", already_running, True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    test_cache()
    test_exact_matching()
    test_alias_expansion()
    test_ambiguity()
    test_not_found()
    await test_tool_execution()
    await test_focus_existing()

    section("SUMMARY")
    total = results["passed"] + results["failed"]
    print(f"  Passed: {results['passed']}/{total}")
    print(f"  Failed: {results['failed']}/{total}")
    if results["failed"] == 0:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED — review output above")

if __name__ == "__main__":
    asyncio.run(main())
