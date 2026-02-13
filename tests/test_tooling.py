from __future__ import annotations

import time

from ax_agent_core.tooling import (
    ToolDefinition,
    ToolExecutionPolicy,
    ToolExecutor,
    ToolSchemaValidator,
)


def test_tool_execution_success() -> None:
    tool = ToolDefinition(
        name="adder",
        description="Adds two numbers",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        },
        handler=lambda payload: {"result": payload["a"] + payload["b"]},
    )

    result = ToolExecutor().execute(tool, {"a": 2, "b": 3})
    assert result.success is True
    assert result.output == {"result": 5}
    assert result.attempts == 1


def test_schema_validation_missing_field() -> None:
    validator = ToolSchemaValidator()
    schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
        "additionalProperties": False,
    }

    try:
        validator.validate(schema, {})
    except Exception as exc:
        assert "required" in str(exc)
    else:
        raise AssertionError("expected schema validation failure")


def test_timeout_returns_failed_result() -> None:
    def slow_handler(_: dict) -> dict:
        time.sleep(0.1)
        return {"ok": True}

    tool = ToolDefinition(
        name="slow",
        description="Slow tool",
        input_schema={"type": "object", "properties": {}, "additionalProperties": True},
        handler=slow_handler,
    )

    result = ToolExecutor().execute(tool, {}, ToolExecutionPolicy(retries=0, timeout_s=0.01))
    assert result.success is False
    assert "timed out" in (result.error or "")
