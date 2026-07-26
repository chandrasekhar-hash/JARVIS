import os
import sys
import time
import asyncio
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unified_context.models import (
    ContextSource,
    ContextPriority,
    ContextProviderInfo,
    ContextChunk,
    CognitiveContext,
)
from unified_context.provider_registry import (
    ProviderRegistry,
    UserModelContextProvider,
    EnvironmentContextProvider,
)
from unified_context.state_assembler import StateAssembler
from unified_context.token_budgeter import TokenBudgeter
from unified_context.engine import UnifiedContextEngine
from brain.event_bus import EventBus


class DummyTestProvider:
    def __init__(self, provider_id: str, priority: ContextPriority = ContextPriority.MEDIUM, should_fail: bool = False):
        self._info = ContextProviderInfo(
            provider_id=provider_id,
            source=ContextSource.RUNTIME,
            name=f"Dummy Provider {provider_id}",
            priority=priority,
        )
        self.should_fail = should_fail

    @property
    def provider_info(self) -> ContextProviderInfo:
        return self._info

    def fetch_context(self, user_id: str, max_tokens: int = 1000) -> list:
        if self.should_fail:
            raise RuntimeError("Provider connection failed!")
        return [
            ContextChunk(
                source=ContextSource.RUNTIME,
                provider_id=self._info.provider_id,
                content=f"Dummy content from {self._info.provider_id}",
                priority=self._info.priority,
                estimated_tokens=10,
            )
        ]

    def check_health(self) -> bool:
        return not self.should_fail


class TestUnifiedContextPhase7(unittest.IsolatedAsyncioTestCase):

    async def test_provider_registration_and_lookup_sla(self):
        registry = ProviderRegistry()
        dummy = DummyTestProvider("p_dummy_1")

        self.assertTrue(registry.register_provider(dummy))

        # Lookup SLA < 20ms
        start = time.perf_counter()
        fetched = registry.get_provider("p_dummy_1")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertLess(elapsed_ms, 20.0)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.provider_info.provider_id, "p_dummy_1")

        # Deregister
        self.assertTrue(registry.remove_provider("p_dummy_1"))
        self.assertIsNone(registry.get_provider("p_dummy_1"))

    async def test_state_assembler_dedup_and_priority_sorting(self):
        assembler = StateAssembler()
        p1 = DummyTestProvider("p_high", priority=ContextPriority.HIGH)
        p2 = DummyTestProvider("p_crit", priority=ContextPriority.CRITICAL)

        chunks = assembler.collect_and_merge([p1, p2], user_id="u1")
        self.assertEqual(len(chunks), 2)
        # CRITICAL priority must come before HIGH priority
        self.assertEqual(chunks[0].priority, ContextPriority.CRITICAL)
        self.assertEqual(chunks[1].priority, ContextPriority.HIGH)

    async def test_token_budgeter_and_overflow_trimming(self):
        budgeter = TokenBudgeter(default_max_budget=50)

        chunks = [
            ContextChunk(source=ContextSource.CONVERSATION, provider_id="p1", content="A" * 100, priority=ContextPriority.CRITICAL, estimated_tokens=25),
            ContextChunk(source=ContextSource.USER_MODEL, provider_id="p2", content="B" * 100, priority=ContextPriority.HIGH, estimated_tokens=25),
            ContextChunk(source=ContextSource.ENVIRONMENT, provider_id="p3", content="C" * 100, priority=ContextPriority.LOW, estimated_tokens=25),
        ]

        budgeted = budgeter.allocate_tokens(chunks, max_budget=50)
        # Only top 2 high-priority chunks should fit within 50 token budget
        self.assertLessEqual(len(budgeted), 2)
        total_tokens = sum(c.estimated_tokens for c in budgeted)
        self.assertLessEqual(total_tokens, 50)

    async def test_unified_context_engine_full_assembly_and_sla(self):
        registry = ProviderRegistry()
        engine = UnifiedContextEngine(registry=registry)

        start = time.perf_counter()
        context = await engine.assemble_context(user_id="u_test", max_budget=4096)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Assembly SLA < 200 ms
        self.assertLess(elapsed_ms, 200.0)
        self.assertIsInstance(context, CognitiveContext)
        self.assertGreater(len(context.chunks), 0)
        self.assertIn("USER_MODEL", context.formatted_prompt_context)

    async def test_provider_failure_resilience(self):
        registry = ProviderRegistry()
        failing_p = DummyTestProvider("p_fail", should_fail=True)
        registry.register_provider(failing_p)

        engine = UnifiedContextEngine(registry=registry)
        context = await engine.assemble_context("u_fail")

        # Context assembly should succeed despite failing provider
        self.assertIsNotNone(context)
        self.assertGreater(len(context.chunks), 0)

    async def test_event_publishing(self):
        custom_bus = EventBus()
        events_emitted = []

        def listener(evt):
            events_emitted.append(evt.name)

        custom_bus.subscribe("ContextUpdated", listener)
        custom_bus.subscribe("ProviderRegistered", listener)
        custom_bus.subscribe("ContextAssemblyCompleted", listener)

        registry = ProviderRegistry(bus=custom_bus)
        engine = UnifiedContextEngine(registry=registry, bus=custom_bus)

        await engine.assemble_context("u_evt")
        await asyncio.sleep(0.05)

        self.assertIn("ProviderRegistered", events_emitted)
        self.assertIn("ContextUpdated", events_emitted)
        self.assertIn("ContextAssemblyCompleted", events_emitted)


if __name__ == "__main__":
    unittest.main()
