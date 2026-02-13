from __future__ import annotations

from ax_agent_core.tooling import ToolDefinition, ToolExecutionPolicy, ToolExecutor


def test_tool_retry_succeeds_on_second_attempt() -> None:
    attempts = {"count": 0}

    def flaky(_: dict) -> dict:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("transient")
        return {"ok": True}

    tool = ToolDefinition(
        name="flaky",
        description="Flaky tool",
        input_schema={"type": "object", "properties": {}, "additionalProperties": True},
        handler=flaky,
    )

    result = ToolExecutor().execute(
        tool,
        {},
        ToolExecutionPolicy(retries=2, timeout_s=1.0, retry_backoff_s=0.0),
    )

    assert result.success is True
    assert result.attempts == 2
    assert result.output == {"ok": True}
