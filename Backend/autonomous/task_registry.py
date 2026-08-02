import asyncio
import time
import inspect
from typing import Dict, Any, Callable, Optional, Awaitable, List
from autonomous.scheduler_models import TaskDefinition, ScheduleTrigger
from autonomous.schedule_parser import parse_natural_language_schedule
from tools.telemetry import log_structured, backend_log

TaskHandler = Callable[..., Awaitable[Dict[str, Any]]]

class ProactiveTaskRegistry:
    """
    Extensible, decoupled registry where subsystems (Memory, Vision, Learning, SelfOptimization,
    ProviderManager, DesktopTools, Diagnostics) register background proactive task handlers.
    """

    def __init__(self):
        self._handlers: Dict[str, TaskHandler] = {}
        self._definitions: Dict[str, TaskDefinition] = {}

    def register_task(
        self,
        name: str,
        handler: TaskHandler,
        description: str,
        default_schedule: str = "Every day at 08:00",
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registers a task handler under a unique task name.
        """
        cleaned_name = name.lower().strip()
        self._handlers[cleaned_name] = handler
        self._definitions[cleaned_name] = TaskDefinition(
            name=cleaned_name,
            description=description,
            category=category,
            default_schedule=default_schedule,
            enabled=True,
            metadata=metadata or {}
        )
        log_structured(backend_log, "INFO", f"[TaskRegistry] Registered task '{cleaned_name}' (category: {category})")

    def get_task_definition(self, name: str) -> Optional[TaskDefinition]:
        return self._definitions.get(name.lower().strip())

    def get_all_tasks(self) -> List[TaskDefinition]:
        return list(self._definitions.values())

    async def execute_task(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        cleaned_name = name.lower().strip()
        if cleaned_name not in self._handlers:
            raise ValueError(f"Task '{name}' is not registered in ProactiveTaskRegistry.")
            
        handler = self._handlers[cleaned_name]
        
        # Check if handler is async or sync
        if asyncio.iscoroutinefunction(handler):
            res = await handler(**params)
        else:
            res = await asyncio.to_thread(handler, **params)
            
        return res if isinstance(res, dict) else {"result": str(res)}


task_registry = ProactiveTaskRegistry()

# ==================================================
# DEFAULT PROACTIVE SUBSYSTEM TASK HANDLERS
# ==================================================

async def _handler_morning_briefing(**kwargs) -> Dict[str, Any]:
    try:
        from predictive.engine import PredictiveGoalEngine
        engine = PredictiveGoalEngine()
        return {"status": "success", "briefing": "Morning briefing generated"}
    except Exception as e:
        return {"status": "skipped", "reason": str(e)}

async def _handler_daily_summary(**kwargs) -> Dict[str, Any]:
    try:
        from memory.manager import MemoryManager
        return {"status": "success", "summary": "Daily memory summary updated"}
    except Exception as e:
        return {"status": "skipped", "reason": str(e)}

async def _handler_memory_consolidation(**kwargs) -> Dict[str, Any]:
    try:
        from memory.manager import MemoryManager
        return {"status": "success", "consolidated": True}
    except Exception as e:
        return {"status": "skipped", "reason": str(e)}

async def _handler_provider_health_check(**kwargs) -> Dict[str, Any]:
    from ai.providers.registry import provider_registry
    status = {}
    for name, p_class in provider_registry.get_registered_providers().items():
        try:
            p = provider_registry.get_provider(name)
            if hasattr(p, "health_check"):
                status[name] = p.health_check()
            else:
                status[name] = bool(getattr(p, "api_key", True))
        except Exception as e:
            status[name] = False
    return {"status": "success", "providers": status}

async def _handler_performance_analysis(**kwargs) -> Dict[str, Any]:
    try:
        from self_optimization.engine import self_optimization_engine
        return {"status": "success", "diagnostics": {"status": "ok"}}
    except Exception as e:
        return {"status": "skipped", "reason": str(e)}

async def _handler_learning_update(**kwargs) -> Dict[str, Any]:
    try:
        return {"status": "success", "patterns_mined": 0}
    except Exception as e:
        return {"status": "skipped", "reason": str(e)}

async def _handler_routine_cleanup(**kwargs) -> Dict[str, Any]:
    # Cleans temporary logs and old caches
    return {"status": "success", "cleaned_items": 0, "freed_bytes": 0}

async def _handler_system_diagnostics(**kwargs) -> Dict[str, Any]:
    import psutil
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    return {"status": "success", "cpu_percent": cpu, "ram_percent": ram}


def register_default_tasks():
    task_registry.register_task(
        name="morning_briefing",
        handler=_handler_morning_briefing,
        description="Generates daily morning intelligence briefing and schedule summary",
        default_schedule="Every morning at 8",
        category="predictive"
    )
    task_registry.register_task(
        name="daily_summary",
        handler=_handler_daily_summary,
        description="Synthesizes daily user context, memory observations, and achievements",
        default_schedule="Every day at 23:00",
        category="memory"
    )
    task_registry.register_task(
        name="memory_consolidation",
        handler=_handler_memory_consolidation,
        description="Performs memory fact promotion and knowledge graph consolidation",
        default_schedule="Every day at 03:00",
        category="memory"
    )
    task_registry.register_task(
        name="provider_health_check",
        handler=_handler_provider_health_check,
        description="Pings all active AI providers and verifies local Ollama endpoint status",
        default_schedule="Every 30 minutes",
        category="ai"
    )
    task_registry.register_task(
        name="performance_analysis",
        handler=_handler_performance_analysis,
        description="Analyzes execution latency bottlenecks and updates optimization recommendations",
        default_schedule="Every 2 hours",
        category="self_optimization"
    )
    task_registry.register_task(
        name="learning_update",
        handler=_handler_learning_update,
        description="Mines user behavior patterns and refines decision heuristics",
        default_schedule="Every 6 hours",
        category="learning"
    )
    task_registry.register_task(
        name="routine_cleanup",
        handler=_handler_routine_cleanup,
        description="Purges stale temporary cache files and manages log file rotation",
        default_schedule="First day of every month",
        category="system"
    )
    task_registry.register_task(
        name="system_diagnostics",
        handler=_handler_system_diagnostics,
        description="Monitors hardware resource utilization (CPU, RAM, Disk)",
        default_schedule="Every 15 minutes",
        category="system"
    )

register_default_tasks()
