from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class ToolSchemaError(ValueError):
    """Raised when tool input does not satisfy the declared schema."""


class ToolExecutionError(RuntimeError):
    """Raised when tool execution fails at runtime (including timeout)."""


@dataclass(frozen=True)
class ToolExecutionPolicy:
    retries: int = 1
    timeout_s: float = 5.0
    retry_backoff_s: float = 0.05


@dataclass
class ToolExecutionResult:
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    attempts: int = 0


@dataclass(frozen=True)
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
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def list(self) -> List[ToolDefinition]:
        return sorted(self._tools.values(), key=lambda item: item.name)


class ToolSchemaValidator:
    """Small JSON-Schema subset validator for runtime tool input checks.

    Supported subset:
    - type: object|string|number|integer|boolean|array|null
    - properties, required, additionalProperties
    - items (for arrays)
    - enum
    - minLength/maxLength for strings
    - minimum/maximum for numbers
    """

    def validate(self, schema: Dict[str, Any], payload: Dict[str, Any]) -> None:
        self._validate_value("$", schema, payload)

    def _validate_value(self, path: str, schema: Dict[str, Any], value: Any) -> None:
        schema_type = schema.get("type")
        if schema_type and not self._matches_type(schema_type, value):
            raise ToolSchemaError(f"{path} expected type {schema_type}")

        if "enum" in schema and value not in schema["enum"]:
            raise ToolSchemaError(f"{path} must be one of {schema['enum']}")

        if schema_type == "object":
            self._validate_object(path, schema, value)
        elif schema_type == "array":
            self._validate_array(path, schema, value)
        elif schema_type == "string":
            self._validate_string(path, schema, value)
        elif schema_type in {"number", "integer"}:
            self._validate_number(path, schema, value)

    def _validate_object(self, path: str, schema: Dict[str, Any], value: Any) -> None:
        if not isinstance(value, dict):
            raise ToolSchemaError(f"{path} must be an object")

        properties = schema.get("properties", {})
        required = schema.get("required", [])
        allow_additional = schema.get("additionalProperties", True)

        for field_name in required:
            if field_name not in value:
                raise ToolSchemaError(f"{path}.{field_name} is required")

        for field_name, field_value in value.items():
            if field_name not in properties:
                if allow_additional:
                    continue
                raise ToolSchemaError(f"{path}.{field_name} is not allowed")
            self._validate_value(f"{path}.{field_name}", properties[field_name], field_value)

    def _validate_array(self, path: str, schema: Dict[str, Any], value: Any) -> None:
        if not isinstance(value, list):
            raise ToolSchemaError(f"{path} must be an array")
        item_schema = schema.get("items")
        if item_schema is None:
            return
        for index, item in enumerate(value):
            self._validate_value(f"{path}[{index}]", item_schema, item)

    def _validate_string(self, path: str, schema: Dict[str, Any], value: Any) -> None:
        if not isinstance(value, str):
            return
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        if min_length is not None and len(value) < int(min_length):
            raise ToolSchemaError(f"{path} is shorter than minLength={min_length}")
        if max_length is not None and len(value) > int(max_length):
            raise ToolSchemaError(f"{path} exceeds maxLength={max_length}")

    def _validate_number(self, path: str, schema: Dict[str, Any], value: Any) -> None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            raise ToolSchemaError(f"{path} must be >= {minimum}")
        if maximum is not None and value > maximum:
            raise ToolSchemaError(f"{path} must be <= {maximum}")

    def _matches_type(self, expected: str, value: Any) -> bool:
        if expected == "string":
            return isinstance(value, str)
        if expected == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "boolean":
            return isinstance(value, bool)
        if expected == "object":
            return isinstance(value, dict)
        if expected == "array":
            return isinstance(value, list)
        if expected == "null":
            return value is None
        return True


class ToolExecutor:
    def __init__(self, validator: Optional[ToolSchemaValidator] = None) -> None:
        self._validator = validator or ToolSchemaValidator()

    def execute(
        self,
        tool: ToolDefinition,
        payload: Dict[str, Any],
        policy: Optional[ToolExecutionPolicy] = None,
    ) -> ToolExecutionResult:
        exec_policy = policy or ToolExecutionPolicy()
        started = time.monotonic()
        attempts = 0
        last_error: Optional[str] = None

        max_attempts = exec_policy.retries + 1
        for attempt in range(1, max_attempts + 1):
            attempts = attempt
            try:
                self._validator.validate(tool.input_schema, payload)
                output = self._run_with_timeout(tool.handler, payload, exec_policy.timeout_s)
                return ToolExecutionResult(
                    tool_name=tool.name,
                    success=True,
                    output=output,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    attempts=attempts,
                )
            except ToolSchemaError as exc:
                return ToolExecutionResult(
                    tool_name=tool.name,
                    success=False,
                    error=str(exc),
                    duration_ms=int((time.monotonic() - started) * 1000),
                    attempts=attempts,
                )
            except (ToolExecutionError, Exception) as exc:
                last_error = str(exc)
                if attempt >= max_attempts:
                    break
                if exec_policy.retry_backoff_s > 0:
                    time.sleep(exec_policy.retry_backoff_s)

        return ToolExecutionResult(
            tool_name=tool.name,
            success=False,
            error=last_error or "unknown tool execution failure",
            duration_ms=int((time.monotonic() - started) * 1000),
            attempts=attempts,
        )

    def _run_with_timeout(
        self,
        handler: Callable[[Dict[str, Any]], Any],
        payload: Dict[str, Any],
        timeout_s: Optional[float],
    ) -> Any:
        if timeout_s is None or timeout_s <= 0:
            return handler(payload)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(handler, payload)
            try:
                return future.result(timeout=timeout_s)
            except FutureTimeout as exc:
                raise ToolExecutionError("tool execution timed out") from exc


def pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True)
