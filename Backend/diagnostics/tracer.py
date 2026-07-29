"""
Distributed Tracer Engine for J.A.R.V.I.S. Phase V1.8.
Tracks trace IDs, nested parent-child span trees, request lifecycles, and execution durations.
"""
import time
import logging
from typing import Dict, List, Optional, Any
from .interfaces import ITracer
from .models import TraceRecord, SpanRecord

logger = logging.getLogger("JARVIS_DistributedTracer")


class DistributedTracer(ITracer):
    """
    Distributed Tracing Engine.
    """

    def __init__(self):
        self._traces: Dict[str, TraceRecord] = {}
        self._active_spans: Dict[str, SpanRecord] = {}

    def start_trace(self, root_operation: str, correlation_id: str = "") -> TraceRecord:
        trace = TraceRecord(root_operation=root_operation, correlation_id=correlation_id)
        self._traces[trace.trace_id] = trace
        logger.info(f"[DistributedTracer] Started trace '{trace.trace_id}' for root operation '{root_operation}'.")
        return trace

    def start_span(self, trace_id: str, operation: str, parent_span_id: Optional[str] = None) -> SpanRecord:
        span = SpanRecord(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation=operation,
            started_at=time.time(),
        )
        self._active_spans[span.span_id] = span

        if trace_id in self._traces:
            self._traces[trace_id].spans.append(span)

        return span

    def finish_span(self, span_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        if span_id in self._active_spans:
            span = self._active_spans.pop(span_id)
            span.ended_at = time.time()
            span.duration_ms = round((span.ended_at - span.started_at) * 1000.0, 2)
            if metadata:
                span.metadata.update(metadata)

            # Update trace total duration
            if span.trace_id in self._traces:
                trace = self._traces[span.trace_id]
                trace.total_duration_ms += span.duration_ms

            logger.info(f"[DistributedTracer] Finished span '{span.span_id}' ({span.operation}) in {span.duration_ms}ms.")

    def get_trace(self, trace_id: str) -> Optional[TraceRecord]:
        return self._traces.get(trace_id)

    def get_all_traces(self) -> List[TraceRecord]:
        return list(self._traces.values())
