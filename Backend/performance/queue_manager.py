"""
Queue Manager with Backpressure Control for J.A.R.V.I.S. Phase V1.7.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from .interfaces import IQueueManager
from .models import QueueStatistics

logger = logging.getLogger("JARVIS_QueueManager")


class PriorityQueueItem:
    def __init__(self, priority: int, item: Any):
        self.priority = priority
        self.item = item

    def __lt__(self, other):
        return self.priority < other.priority


class QueueManager(IQueueManager):
    """
    Priority event queue manager featuring backpressure limits and overflow protection.
    """

    def __init__(self, default_capacity: int = 1000):
        self.default_capacity = default_capacity
        self._queues: Dict[str, asyncio.PriorityQueue] = {}
        self._enqueued_counts: Dict[str, int] = {}
        self._dequeued_counts: Dict[str, int] = {}
        self._overflow_drops: Dict[str, int] = {}

    def _get_queue(self, queue_name: str) -> asyncio.PriorityQueue:
        if queue_name not in self._queues:
            self._queues[queue_name] = asyncio.PriorityQueue(maxsize=self.default_capacity)
            self._enqueued_counts[queue_name] = 0
            self._dequeued_counts[queue_name] = 0
            self._overflow_drops[queue_name] = 0
        return self._queues[queue_name]

    async def enqueue(self, queue_name: str, item: Any, priority: int = 5) -> bool:
        q = self._get_queue(queue_name)
        if q.full():
            # Backpressure overflow protection: drop item and log warning
            self._overflow_drops[queue_name] += 1
            logger.warning(f"[QueueManager] Queue '{queue_name}' is FULL ({self.default_capacity}). Dropping incoming item.")
            return False

        await q.put(PriorityQueueItem(priority=priority, item=item))
        self._enqueued_counts[queue_name] += 1
        return True

    async def dequeue(self, queue_name: str) -> Any:
        q = self._get_queue(queue_name)
        pq_item: PriorityQueueItem = await q.get()
        self._dequeued_counts[queue_name] += 1
        return pq_item.item

    def get_statistics(self, queue_name: str = "default") -> QueueStatistics:
        q = self._queues.get(queue_name)
        curr_size = q.qsize() if q else 0
        return QueueStatistics(
            queue_name=queue_name,
            current_size=curr_size,
            max_capacity=self.default_capacity,
            total_enqueued=self._enqueued_counts.get(queue_name, 0),
            total_dequeued=self._dequeued_counts.get(queue_name, 0),
            overflow_drops=self._overflow_drops.get(queue_name, 0),
        )
