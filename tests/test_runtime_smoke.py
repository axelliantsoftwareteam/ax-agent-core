from __future__ import annotations

from ax_agent_core.demo import build_demo_agent


def test_ops_assistant_smoke_flow() -> None:
    agent = build_demo_agent("examples/config.json")

    r1 = agent.runtime.handle('tool:math {"expression": "2+2"}', session_id="smoke")
    assert r1.tool_result is not None
    assert r1.tool_result.success is True
    assert r1.tool_result.output["result"] == 4.0

    r2 = agent.runtime.handle(
        'tool:http_get {"url": "https://status.axelliant.internal/health"}',
        session_id="smoke",
    )
    assert r2.tool_result is not None
    assert r2.tool_result.success is True
    assert r2.tool_result.output["status"] == 200

    r3 = agent.runtime.handle("give me a short summary", session_id="smoke")
    assert r3.provider_response is not None
    assert r3.provider_response.provider == "mock"

    health = agent.mcp_bridge.health()
    assert health["mcp_ready"] is True
