from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .cost import CostTracker
from .memory import ConversationMemory, Message
from .observability import OpenTelemetryHook, StructuredLogger
from .providers import ModelRouter, ProviderRequest, ProviderResponse
from .tooling import ToolExecutionPolicy, ToolExecutionResult, ToolExecutor, ToolRegistry


@dataclass(frozen=True)
class ParsedToolCall:
    name: str
    payload: dict[str, Any]


@dataclass
class AgentResponse:
    content: str
    session_id: str
    tool_result: ToolExecutionResult | None = None
    provider_response: ProviderResponse | None = None


class AgentRuntime:
    def __init__(
        self,
        registry: ToolRegistry,
        router: ModelRouter,
        memory: ConversationMemory,
        cost_tracker: CostTracker,
        logger: StructuredLogger | None = None,
        telemetry: OpenTelemetryHook | None = None,
        executor: ToolExecutor | None = None,
        execution_policy: ToolExecutionPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._router = router
        self._memory = memory
        self._cost_tracker = cost_tracker
        self._logger = logger or StructuredLogger("ax_agent_core.runtime")
        self._telemetry = telemetry or OpenTelemetryHook(enabled=False)
        self._executor = executor or ToolExecutor()
        self._execution_policy = execution_policy or ToolExecutionPolicy()

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def handle(self, user_input: str, session_id: str = "default") -> AgentResponse:
        self._memory.append(session_id, Message(role="user", content=user_input))
        self._logger.info("user_message", session_id=session_id, content=user_input)

        tool_call = self._parse_tool_call(user_input)
        if tool_call:
            return self._handle_tool_call(tool_call, session_id)

        with self._telemetry.span("provider.generate", {"session_id": session_id}):
            provider_response = self._router.generate(ProviderRequest(prompt=user_input))

        self._cost_tracker.record(provider_response.usage)
        self._memory.append(session_id, Message(role="assistant", content=provider_response.text))
        self._logger.info(
            "provider_response",
            session_id=session_id,
            provider=provider_response.provider,
            usage=provider_response.usage,
        )
        return AgentResponse(
            content=provider_response.text,
            session_id=session_id,
            provider_response=provider_response,
        )

    def _handle_tool_call(self, tool_call: ParsedToolCall, session_id: str) -> AgentResponse:
        tool = self._registry.get(tool_call.name)
        self._logger.info("tool_execution_start", session_id=session_id, tool=tool.name)

        with self._telemetry.span("tool.execute", {"tool.name": tool.name}):
            result = self._executor.execute(tool, tool_call.payload, policy=self._execution_policy)

        if result.success:
            content = f"Tool '{result.tool_name}' executed successfully."
            self._memory.append(session_id, Message(role="tool", content=json.dumps(result.output)))
        else:
            content = f"Tool '{result.tool_name}' failed: {result.error}"
            self._memory.append(session_id, Message(role="tool", content=content))

        self._logger.info(
            "tool_execution_end",
            session_id=session_id,
            tool=result.tool_name,
            success=result.success,
            attempts=result.attempts,
            duration_ms=result.duration_ms,
        )

        self._memory.append(session_id, Message(role="assistant", content=content))
        return AgentResponse(content=content, session_id=session_id, tool_result=result)

    @staticmethod
    def _parse_tool_call(user_input: str) -> ParsedToolCall | None:
        text = user_input.strip()
        if not text.startswith("tool:"):
            return None

        # format: tool:<tool_name> {json-payload}
        parts = text.split(" ", 1)
        tool_name = parts[0][5:].strip()
        payload: dict[str, Any] = {}

        if len(parts) == 2 and parts[1].strip():
            payload = json.loads(parts[1])
            if not isinstance(payload, dict):
                raise ValueError("tool payload must be a JSON object")

        if not tool_name:
            raise ValueError("tool name is required")

        return ParsedToolCall(name=tool_name, payload=payload)
