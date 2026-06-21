from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, nullcontext
from dataclasses import dataclass, field
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

_tracer_provider = None
_otel_tracer: trace.Tracer | None = None


def init_arize(settings: Settings | None = None) -> bool:
    """Register Arize OTel exporter. Returns True when cloud export is active."""
    global _tracer_provider, _otel_tracer

    cfg = settings or get_settings()
    if not cfg.arize_enabled or not cfg.arize_api_key or not cfg.arize_space_id:
        logger.info("Arize tracing disabled (set ARIZE_ENABLED=true and credentials in .env)")
        return False

    if _tracer_provider is not None:
        return True

    try:
        from arize.otel import register
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        _tracer_provider = register(
            space_id=cfg.arize_space_id,
            api_key=cfg.arize_api_key,
            project_name=cfg.arize_project_name,
        )
        HTTPXClientInstrumentor().instrument(tracer_provider=_tracer_provider)
        _otel_tracer = trace.get_tracer("orchestrateai")
        logger.info(
            "Arize tracing enabled (project=%s space=%s…)",
            cfg.arize_project_name,
            cfg.arize_space_id[:8],
        )
        return True
    except Exception:
        logger.exception("Failed to initialize Arize tracing")
        return False


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
    """Local span buffer + optional Arize OTel export."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._spans: list[TraceSpan] = []
        self._cloud = init_arize(self._settings)

    @property
    def enabled(self) -> bool:
        return self._cloud

    @asynccontextmanager
    async def span(self, name: str, **attributes: Any) -> AsyncIterator[TraceSpan]:
        trace_span = TraceSpan(name=name, attributes=attributes)
        otel_ctx = (
            _otel_tracer.start_as_current_span(name, attributes=attributes)
            if self._cloud and _otel_tracer is not None
            else nullcontext()
        )

        with otel_ctx:
            try:
                yield trace_span
            except Exception as exc:
                span = trace.get_current_span()
                if span.is_recording():
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                raise
            finally:
                trace_span.end_ms = time.time() * 1000
                self._spans.append(trace_span)
                span = trace.get_current_span()
                if span.is_recording() and trace_span.latency_ms is not None:
                    span.set_attribute("latency_ms", trace_span.latency_ms)
                logger.debug(
                    "trace span: %s latency_ms=%.1f cloud=%s",
                    name,
                    trace_span.latency_ms or 0,
                    self._cloud,
                )

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
