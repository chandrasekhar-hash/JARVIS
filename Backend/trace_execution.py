"""
Full end-to-end execution trace for JARVIS tool dispatch.
"""
import sys
import os
import asyncio
import inspect
import importlib

sys.path.insert(0, r'd:\JARVIS\Backend')

# ─── STEP 1: Module path check ──────────────────────────────────────────────
print("=" * 60)
print("[STEP 1] Module File Paths")
print("=" * 60)

# Use importlib to get the actual module, not the singleton object
registry_mod  = importlib.import_module("tools.registry")
router_mod    = importlib.import_module("tools.router")
apps_mod      = importlib.import_module("tools.apps")
clf_mod       = importlib.import_module("tools.classifier")

print(f"  tools.registry module  : {registry_mod.__file__}")
print(f"  tools.router module    : {router_mod.__file__}")
print(f"  tools.apps module      : {apps_mod.__file__}")
print(f"  tools.classifier module: {clf_mod.__file__}")

# ─── STEP 2: Trigger all tool registrations ─────────────────────────────────
import tools  # imports browser, apps, filesystem registrations

from tools.registry import registry, ToolRegistry

# ─── STEP 3: execute() signature audit ──────────────────────────────────────
print()
print("=" * 60)
print("[STEP 2] execute() Signature Audit")
print("=" * 60)

sig = inspect.signature(ToolRegistry.execute)
params = list(sig.parameters.keys())  # includes 'self'
print(f"  ToolRegistry.execute params : {params}")

has_name_param     = "name" in params
has_tool_name_param = "tool_name" in params

if has_name_param:
    print("  !! FAIL: 'name' parameter still in execute() — COLLISION RISK for app tools!")
elif has_tool_name_param:
    print("  PASS: execute() uses 'tool_name' — safe, no collision with app 'name' args")
else:
    print(f"  WARNING: Unexpected params: {params}")

# ─── STEP 4: Singleton identity check ───────────────────────────────────────
print()
print(f"  ToolRegistry class id         : {id(ToolRegistry)}")
registry_from_module = registry_mod.registry
print(f"  registry_mod.registry id      : {id(registry_from_module)}")
print(f"  registry (direct import) id   : {id(registry)}")
router_registry = getattr(router_mod, 'registry', None)
print(f"  router_mod.registry id        : {id(router_registry)}")
print(f"  All same singleton?           : {(registry is registry_from_module) and (registry is router_registry)}")

# ─── STEP 5: Tool schema audit ──────────────────────────────────────────────
print()
print("=" * 60)
print("[STEP 3] Tool Schema Audit — Parameters Named 'name'")
print("=" * 60)
for tname, tool in registry.tools.items():
    props = tool.parameters.get("properties", {})
    param_names = list(props.keys())
    flag = "  <<< has 'name' arg" if "name" in param_names else ""
    print(f"  {tname:30s}: {param_names}{flag}")

# ─── STEP 6: Live execution trace ───────────────────────────────────────────
print()
print("=" * 60)
print("[STEP 4-6] Full Execution Path Trace")
print("=" * 60)

async def run_traces():
    commands = [
        "Open YouTube",
        "Open Chrome",
        "Open VS Code",
        "Close Chrome",
    ]

    for cmd in commands:
        print()
        print(f"{'─'*60}")
        print(f"  COMMAND: {cmd!r}")

        # A. Classifier stage
        direct_match = clf_mod.classify_intent(cmd)
        print(f"  [A] Classifier output      : {direct_match}")

        if not direct_match:
            print(f"  [A] No direct match — would route to LLM path")
            continue

        tool_name = direct_match["tool_name"]
        tool_args = direct_match["arguments"]

        # B. Router payload pre-execute check
        print(f"  [B] Router payload:")
        print(f"       tool_name  = {tool_name!r}")
        print(f"       tool_args  = {tool_args}")

        # C. Collision check
        exec_param_names = [p for p in params if p != "self"]
        collisions = [k for k in tool_args if k in exec_param_names]
        print(f"  [C] execute() param names  : {exec_param_names}")
        print(f"  [C] tool_args keys         : {list(tool_args.keys())}")
        if collisions:
            print(f"  [C] !! COLLISION DETECTED: {collisions} appear in both execute() params AND tool_args!")
        else:
            print(f"  [C] SAFE — no key overlap between execute() params and tool_args")

        # D. Actual execute call
        print(f"  [D] Calling: registry.execute({tool_name!r}, **{tool_args})")
        try:
            result = await registry.execute(tool_name, **tool_args)
            short = str(result)[:80] + ("..." if len(str(result)) > 80 else "")
            print(f"  [E] Result                 : {short}")
        except TypeError as e:
            print(f"  [E] !! TypeError (COLLISION): {e}")
        except Exception as e:
            print(f"  [E] ERROR ({type(e).__name__})  : {e}")

    print()
    print("=" * 60)
    print("[DONE] Trace complete")
    print("=" * 60)

asyncio.run(run_traces())
