from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class ToolSchemaError(ValueError):
    pass


class ToolExecutionError(RuntimeError):
    pass


@dataclass
class ToolExecutionResult:
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Any]


@dataclass
class ToolRegistry:
    _tools: Dict[str, ToolDefinition] = field(default_factory=dict)

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def list(self) -> List[ToolDefinition]:
        return list(self._tools.values())


class ToolSchemaValidator:
    """Minimal JSON Schema validator for object inputs.

    Supports: type=object, properties, required, additionalProperties.
    """

    def validate(self, schema: Dict[str, Any], payload: Dict[str, Any]) -> None:
        if schema.get("type") != "object":
            raise ToolSchemaError("Schema root must be an object")
        if not isinstance(payload, dict):
            raise ToolSchemaError("Tool input must be an object")

        properties = schema.get("properties", {})
        required = schema.get("required", [])
        allow_additional = schema.get("additionalProperties", True)

        for key in required:
            if key not in payload:
                raise ToolSchemaError(f"Missing required field: {key}")

        for key, value in payload.items():
            if key not in properties:
                if not allow_additional:
                    raise ToolSchemaError(f"Unexpected field: {key}")
                continue
            expected_type = properties[key].get("type")
            if expected_type is None:
                continue
            if not self._matches_type(expected_type, value):
                raise ToolSchemaError(
                    f"Field '{key}' expected type {expected_type}"
                )

    def _matches_type(self, expected: str, value: Any) -> bool:
        mapping = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
            "null": type(None),
        }
        if expected not in mapping:
            return True
        return isinstance(value, mapping[expected])


class ToolExecutor:
    def __init__(self, validator: Optional[ToolSchemaValidator] = None) -> None:
        self._validator = validator or ToolSchemaValidator()

    def execute(
        self,
        tool: ToolDefinition,
        payload: Dict[str, Any],
        retries: int = 0,
        timeout_s: Optional[float] = None,
    ) -> ToolExecutionResult:
        start = time.time()
        attempt = 0
        last_error: Optional[str] = None
        while attempt <= retries:
            attempt += 1
            try:
                self._validator.validate(tool.input_schema, payload)
                output = self._run_with_timeout(tool.handler, payload, timeout_s)
                duration_ms = int((time.time() - start) * 1000)
                return ToolExecutionResult(
                    tool_name=tool.name,
                    success=True,
                    output=output,
                    duration_ms=duration_ms,
                )
            except (ToolSchemaError, ToolExecutionError, Exception) as exc:
                last_error = str(exc)
        duration_ms = int((time.time() - start) * 1000)
        return ToolExecutionResult(
            tool_name=tool.name,
            success=False,
            error=last_error,
            duration_ms=duration_ms,
        )

    def _run_with_timeout(
        self,
        handler: Callable[[Dict[str, Any]], Any],
        payload: Dict[str, Any],
        timeout_s: Optional[float],
    ) -> Any:
        if timeout_s is None:
            return handler(payload)

        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(handler, payload)
            try:
                return future.result(timeout=timeout_s)
            except FutureTimeout as exc:
                raise ToolExecutionError("Tool execution timed out") from exc


def pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True)
