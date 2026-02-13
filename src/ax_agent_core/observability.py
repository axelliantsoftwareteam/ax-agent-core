from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional


class StructuredLogger:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(_JsonFormatter())
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def info(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        payload = {"event": event}
        if data:
            payload.update(data)
        self._logger.info(payload)

    def error(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        payload = {"event": event}
        if data:
            payload.update(data)
        self._logger.error(payload)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, dict):
            payload = record.msg
        else:
            payload = {"message": record.getMessage()}
        payload.update({"level": record.levelname, "logger": record.name})
        return json.dumps(payload)


class OpenTelemetryHook:
    """Optional OpenTelemetry helper without hard dependency."""

    def __init__(self, service_name: str = "ax-agent-core") -> None:
        self.service_name = service_name
        self._tracer = None
        self._available = False
        try:
            from opentelemetry import trace  # type: ignore
            from opentelemetry.sdk.resources import Resource  # type: ignore
            from opentelemetry.sdk.trace import TracerProvider  # type: ignore

            provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(service_name)
            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def start_span(self, name: str):
        if not self._available or self._tracer is None:
            return _NoopSpan()
        return self._tracer.start_as_current_span(name)


class _NoopSpan:
    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None
