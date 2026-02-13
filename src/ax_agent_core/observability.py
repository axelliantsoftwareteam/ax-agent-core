from __future__ import annotations

import json
import logging
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, dict):
            payload = dict(record.msg)
        else:
            payload = {"message": record.getMessage()}

        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        payload.setdefault("level", record.levelname)
        payload.setdefault("logger", record.name)
        return json.dumps(payload, sort_keys=True)


class StructuredLogger:
    """JSON logger for runtime and tool telemetry events."""

    def __init__(self, name: str, level: str = "INFO") -> None:
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(_JsonFormatter())
            logger.addHandler(handler)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._logger = logger

    def info(self, event: str, **fields: Any) -> None:
        payload = {"event": event, **fields}
        self._logger.info(payload)

    def error(self, event: str, **fields: Any) -> None:
        payload = {"event": event, **fields}
        self._logger.error(payload)


class OpenTelemetryHook:
    """Optional OpenTelemetry wrapper with no hard dependency.

    If opentelemetry packages are unavailable, this class gracefully falls back
    to a no-op span context manager.
    """

    def __init__(self, service_name: str = "ax-agent-core", enabled: bool = False) -> None:
        self._enabled = enabled
        self._tracer = None
        self._available = False

        if not enabled:
            return

        try:
            from opentelemetry import trace  # type: ignore
            from opentelemetry.sdk.resources import Resource  # type: ignore
            from opentelemetry.sdk.trace import TracerProvider  # type: ignore

            provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(service_name)
            self._available = True
        except Exception:
            self._tracer = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    @contextmanager
    def span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[None, None, None]:
        if not self._available or self._tracer is None:
            yield
            return

        with self._tracer.start_as_current_span(name) as span:
            for key, value in (attributes or {}).items():
                span.set_attribute(key, value)
            yield
