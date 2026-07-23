import asyncio
from typing import Optional, List, Dict, Any
from brain.context import BaseContextProvider
from memory.models.query import MemoryQuery
from memory.retrieval.pipeline import retrieval_pipeline, RetrievalPipeline
from tools.telemetry import log_structured, backend_log


class MemoryContextProvider(BaseContextProvider):
    """
    Modular Context Provider integrating the Memory Subsystem into the Brain's context pipeline.
    Invokes RetrievalPipeline to retrieve relevant long-term memories without exposing raw storage drivers
    or coupling MemoryManager directly to Brain reasoning loops.
    """

    def __init__(self, pipeline: Optional[RetrievalPipeline] = None):
        self.pipeline = pipeline or retrieval_pipeline

    @property
    def name(self) -> str:
        return "Memory"

    def should_provide_context(self, intent: str) -> bool:
        """
        Determines whether memory context should be fetched for the given user intent string.
        Returns True for non-empty query intents.
        """
        if not intent or not intent.strip():
            return False

        intent_lower = intent.lower()
        # Memory triggers or general conversational context
        triggers = [
            "remember", "recall", "what did i", "preference", "user", "who", "history",
            "previous", "favorite", "my", "last time", "fact", "project", "code", "file", "app"
        ]
        return any(trig in intent_lower for trig in triggers) or len(intent.strip()) > 3

    def get_context(self, intent: str) -> Optional[str]:
        """
        Invokes RetrievalPipeline synchronously to produce formatted LLM memory context.
        """
        if not self.should_provide_context(intent):
            return None

        try:
            query = MemoryQuery(query_text=intent, top_k=5)

            # Helper function to execute async pipeline
            async def _fetch():
                return await self.pipeline.execute(query)

            # Handle running vs main event loops
            try:
                loop = asyncio.get_running_loop()
                # If running in async loop thread, execute in separate task/future
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    package = pool.submit(lambda: asyncio.run(_fetch())).result(timeout=3.0)
            except RuntimeError:
                package = asyncio.run(_fetch())

            if package and package.has_context:
                log_structured(backend_log, "INFO", f"[MemoryContextProvider] Injected {package.memory_count} memories into Brain context.")
                return package.formatted_context

        except Exception as e:
            log_structured(backend_log, "WARNING", f"[MemoryContextProvider] Retrieval error: {str(e)}")

        return None


# Singleton instance of MemoryContextProvider
memory_context_provider = MemoryContextProvider()
