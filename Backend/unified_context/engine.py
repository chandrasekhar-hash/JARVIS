import time
import asyncio
from typing import List, Dict, Optional, Any
from unified_context.models import (
    CognitiveContext,
    ContextAssemblyMetrics,
    ContextChunk,
    ContextSource,
)
from unified_context.interfaces import (
    IProviderRegistry,
    IStateAssembler,
    ITokenBudgeter,
)
from unified_context.provider_registry import provider_registry, ProviderRegistry
from unified_context.state_assembler import StateAssembler
from unified_context.token_budgeter import TokenBudgeter
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class UnifiedContextEngine:
    """
    Main Unified Context Engine for Milestone 7.4.
    Assembles a single unified CognitiveContext snapshot representing all available knowledge.
    SLA Target: Context Assembly < 200 ms.
    Does NOT predict goals, execute workflows, optimize runtime, or learn preferences.
    """

    def __init__(
        self,
        registry: Optional[IProviderRegistry] = None,
        assembler: Optional[IStateAssembler] = None,
        budgeter: Optional[ITokenBudgeter] = None,
        bus: Optional[EventBus] = None,
    ):
        self.registry = registry or provider_registry
        self.assembler = assembler or StateAssembler()
        self.budgeter = budgeter or TokenBudgeter()
        self.event_bus = bus or event_bus

    async def assemble_context(
        self, user_id: str = "default_user", max_budget: int = 4096
    ) -> CognitiveContext:
        start_time = time.perf_counter()
        try:
            # Step 1 & 2: Provider Collection & Health Validation
            providers = self.registry.list_providers()
            healthy_providers = [p for p in providers if p.check_health()]

            # Step 3, 4, 5, 6: Parallel Collection, Merge, Deduplicate, Priority Ranking
            collected_chunks = self.assembler.collect_and_merge(
                providers=healthy_providers, user_id=user_id
            )
            total_collected = len(collected_chunks)

            # Step 7 & 8: Token Allocation & Trim Overflow
            budgeted_chunks = self.budgeter.allocate_tokens(
                chunks=collected_chunks, max_budget=max_budget
            )
            chunks_after_trim = len(budgeted_chunks)

            total_tokens_used = sum(
                c.estimated_tokens or (len(c.content) // 4) for c in budgeted_chunks
            )
            sources_included = list(set(c.source for c in budgeted_chunks))

            # Step 9: Generate Context & Formatted Prompt Context
            formatted_blocks: List[str] = []
            for c in budgeted_chunks:
                formatted_blocks.append(f"=== [{c.source.value.upper()}] ===\n{c.content}")

            formatted_prompt_context = "\n\n".join(formatted_blocks)

            assembly_time_ms = (time.perf_counter() - start_time) * 1000.0

            metrics = ContextAssemblyMetrics(
                total_chunks_collected=total_collected,
                chunks_after_dedup=total_collected,
                chunks_after_trim=chunks_after_trim,
                total_tokens_budgeted=max_budget,
                total_tokens_used=total_tokens_used,
                assembly_time_ms=assembly_time_ms,
                timestamp=time.time(),
            )

            cognitive_context = CognitiveContext(
                user_id=user_id,
                chunks=budgeted_chunks,
                formatted_prompt_context=formatted_prompt_context,
                token_count=total_tokens_used,
                sources_included=sources_included,
                assembly_metrics=metrics,
                timestamp=time.time(),
            )

            # Step 10: Publish Events
            self.event_bus.emit(
                "ContextUpdated",
                context_id=cognitive_context.context_id,
                user_id=user_id,
                token_count=total_tokens_used,
                sources_count=len(sources_included),
            )

            self.event_bus.emit(
                "ContextAssemblyCompleted",
                assembly_id=metrics.assembly_id,
                assembly_time_ms=assembly_time_ms,
                total_tokens=total_tokens_used,
            )

            if total_tokens_used >= max_budget:
                self.event_bus.emit(
                    "BudgetExceeded",
                    context_id=cognitive_context.context_id,
                    requested_tokens=total_tokens_used,
                    budget=max_budget,
                )

            if assembly_time_ms > 200.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[UnifiedContextEngine] Context Assembly SLA threshold exceeded: {assembly_time_ms:.2f} ms",
                )

            log_structured(
                backend_log,
                "INFO",
                f"[UnifiedContextEngine] Assembled context '{cognitive_context.context_id}' ({total_tokens_used} tokens) in {assembly_time_ms:.2f} ms",
            )
            return cognitive_context

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[UnifiedContextEngine] Assembly error: {str(e)}")
            assembly_time_ms = (time.perf_counter() - start_time) * 1000.0
            return CognitiveContext(
                user_id=user_id,
                formatted_prompt_context="[Context Assembly Error]",
                assembly_metrics=ContextAssemblyMetrics(assembly_time_ms=assembly_time_ms),
            )


# Default global instance
unified_context_engine = UnifiedContextEngine()
