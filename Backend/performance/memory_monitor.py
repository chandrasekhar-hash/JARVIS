"""
Memory Monitor for J.A.R.V.I.S. Phase V1.7.
Tracks RAM RSS, VMS, GC collections, peak allocations, and memory leak warnings.
"""
import gc
import sys
import psutil
import logging
from .interfaces import IMemoryMonitor
from .models import MemoryStatistics

logger = logging.getLogger("JARVIS_MemoryMonitor")


class MemoryMonitor(IMemoryMonitor):
    """
    Process memory allocation and garbage collection monitor.
    """

    def __init__(self):
        self._process = psutil.Process()
        self._peak_rss_mb: float = 0.0

    def get_statistics(self) -> MemoryStatistics:
        try:
            mem_info = self._process.memory_info()
            rss_mb = round(mem_info.rss / (1024 * 1024), 2)
            vms_mb = round(mem_info.vms / (1024 * 1024), 2)
        except Exception:
            rss_mb = 0.0
            vms_mb = 0.0

        if rss_mb > self._peak_rss_mb:
            self._peak_rss_mb = rss_mb

        gc_stats = gc.get_count()
        gen0 = gc_stats[0] if len(gc_stats) > 0 else 0
        gen1 = gc_stats[1] if len(gc_stats) > 1 else 0
        gen2 = gc_stats[2] if len(gc_stats) > 2 else 0

        return MemoryStatistics(
            rss_mb=rss_mb,
            vms_mb=vms_mb,
            peak_mb=self._peak_rss_mb,
            gc_gen0_collections=gen0,
            gc_gen1_collections=gen1,
            gc_gen2_collections=gen2,
            allocation_count=sys.gettotalrefcount() if hasattr(sys, "gettotalrefcount") else 0,
        )

    def force_garbage_collection(self) -> int:
        """Triggers immediate Python GC collection pass."""
        collected = gc.collect()
        logger.info(f"[MemoryMonitor] Forced GC collect pass freed {collected} objects.")
        return collected
