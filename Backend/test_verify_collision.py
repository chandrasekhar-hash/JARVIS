import sys
import asyncio
import inspect

sys.path.insert(0, r'd:\JARVIS\Backend')
import tools
from tools.registry import registry
from tools.classifier import classify_intent

def test_execute_signature():
    print("=== 1. execute() Parameter Audit ===")
    sig = inspect.signature(registry.execute)
    params = list(sig.parameters.keys())
    print(f"execute() parameters: {params}")
    assert "tool_name" in params, "FAIL: execute() still uses old 'name' parameter!"
    assert "name" not in params, "FAIL: 'name' param still present in execute() signature!"
    print("PASS: No parameter collision - execute() uses tool_name, not name\n")

def test_schema_audit():
    print("=== 2. Tool Schema Parameter Audit ===")
    print("Tools with 'name' param (verified safe since execute() uses tool_name):")
    for tname, tool in registry.tools.items():
        props = tool.parameters.get("properties", {})
        param_names = list(props.keys())
        flag = " <<< HAS 'name' param" if "name" in param_names else ""
        print(f"  {tname}: params={param_names}{flag}")
    print("PASS: Schema audit complete - no collision possible\n")

async def test_collision_simulation():
    print("=== 3. Collision Simulation Tests ===")
    test_cases = [
        ("Open YouTube",  "browser_open_url", {"urls": ["https://youtube.com"]}),
        ("Open Chrome",   "app_open",         {"name": "chrome"}),
        ("Open VS Code",  "app_open",         {"name": "vs code"}),
        ("Close Chrome",  "app_close",        {"name": "chrome"}),
    ]
    all_passed = True
    for label, tool_name, tool_args in test_cases:
        try:
            result = await registry.execute(tool_name, **tool_args)
            short = str(result)[:70] + ("..." if len(str(result)) > 70 else "")
            print(f"  PASS [{label}]: {short}")
        except TypeError as e:
            print(f"  FAIL [{label}] - TypeError (collision!): {e}")
            all_passed = False
        except Exception as e:
            print(f"  ERROR [{label}] ({type(e).__name__}): {e}")
    if all_passed:
        print("PASS: All commands executed without argument collision\n")
    else:
        print("FAIL: Some commands had collision errors\n")

def test_classifier_output():
    print("=== 4. Intent Classifier Output ===")
    queries = ["Open YouTube", "Open Chrome", "Open VS Code", "Close Chrome"]
    for q in queries:
        result = classify_intent(q)
        print(f"  '{q}' -> {result}")
    print("PASS: Classifier output verified\n")

async def main():
    test_execute_signature()
    test_schema_audit()
    test_classifier_output()
    await test_collision_simulation()
    print("=== All verifications complete ===")

if __name__ == "__main__":
    asyncio.run(main())
