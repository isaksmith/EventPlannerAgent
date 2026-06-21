from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, TypeVar

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class TraceSpan:
    name: str
    start_ms: float = field(default_factory=lambda: time.time() * 1000)
    end_ms: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def latency_ms(self) -> float | None:
        if self.end_ms is None:
            return None
        return self.end_ms - self.start_ms


class ArizeTracer:
    """Tracing wrapper — no-op when Arize is disabled."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._spans: list[TraceSpan] = []

    @property
    def enabled(self) -> bool:
        return self._settings.arize_enabled and bool(self._settings.arize_api_key)

    @asynccontextmanager
    async def span(self, name: str, **attributes: Any) -> AsyncIterator[TraceSpan]:
        trace = TraceSpan(name=name, attributes=attributes)
        if self.enabled:
            logger.debug("arize span start: %s %s", name, attributes)
        try:
            yield trace
        finally:
            trace.end_ms = time.time() * 1000
            self._spans.append(trace)
            if self.enabled:
                logger.info(
                    "arize span end: %s latency_ms=%.1f attrs=%s",
                    name,
                    trace.latency_ms or 0,
                    attributes,
                )
            else:
                logger.debug("trace span: %s latency_ms=%.1f", name, trace.latency_ms or 0)

    async def trace_call(self, name: str, fn: Callable[[], T], **attributes: Any) -> T:
        async with self.span(name, **attributes):
            result = fn()
            if hasattr(result, "__await__"):
                return await result  # type: ignore[misc]
            return result

    def recent_spans(self) -> list[TraceSpan]:
        return list(self._spans)


_tracer: ArizeTracer | None = None


def get_tracer(settings: Settings | None = None) -> ArizeTracer:
    global _tracer
    if _tracer is None:
        _tracer = ArizeTracer(settings)
    return _tracer
