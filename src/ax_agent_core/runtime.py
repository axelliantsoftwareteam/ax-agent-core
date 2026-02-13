from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .cost import CostTracker
from .memory import ConversationStore, Message
from .observability import StructuredLogger
from .providers import ModelRouter, ProviderResponse
from .tooling import ToolExecutor, ToolRegistry, ToolExecutionResult


@dataclass
class AgentResponse:
    content: str
    tool_result: Optional[ToolExecutionResult] = None
    provider_response: Optional[ProviderResponse] = None


class AgentRuntime:
    def __init__(
        self,
        registry: ToolRegistry,
        router: ModelRouter,
        memory: ConversationStore,
        cost_tracker: CostTracker,
        logger: Optional[StructuredLogger] = None,
        executor: Optional[ToolExecutor] = None,
    ) -> None:
        self._registry = registry
        self._router = router
        self._memory = memory
        self._cost_tracker = cost_tracker
        self._logger = logger or StructuredLogger("ax_agent_core")
        self._executor = executor or ToolExecutor()

    def handle(self, user_input: str, session_id: str = "default") -> AgentResponse:
        self._memory.append(session_id, Message(role="user", content=user_input))
        self._logger.info("user_message", {"session_id": session_id, "content": user_input})

        tool_request = self._maybe_parse_tool_request(user_input)
        tool_result = None
        if tool_request:
            tool_result = self._execute_tool(tool_request, session_id)
            if tool_result.success:
                content = f"Tool '{tool_result.tool_name}' executed successfully."
            else:
                content = f"Tool '{tool_result.tool_name}' failed: {tool_result.error}"
            self._memory.append(session_id, Message(role="tool", content=content))
            return AgentResponse(content=content, tool_result=tool_result)

        provider_response = self._router.generate(user_input)
        content = provider_response.text
        self._memory.append(session_id, Message(role="assistant", content=content))
        self._cost_tracker.record(provider_response.usage)
        self._logger.info(
            "provider_response",
            {"session_id": session_id, "provider": provider_response.provider, "tokens": provider_response.usage.get("tokens")},
        )
        return AgentResponse(content=content, provider_response=provider_response)

    def _maybe_parse_tool_request(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Simple parser for demo usage: `tool:<name> {json}`"""
        if not user_input.strip().startswith("tool:"):
            return None
        parts = user_input.split(" ", 1)
        tool_name = parts[0][5:]
        payload = {}
        if len(parts) > 1:
            try:
                import json

                payload = json.loads(parts[1])
            except json.JSONDecodeError:
                payload = {"raw": parts[1]}
        return {"name": tool_name, "payload": payload}

    def _execute_tool(self, request: Dict[str, Any], session_id: str) -> ToolExecutionResult:
        tool = self._registry.get(request["name"])
        self._logger.info(
            "tool_execution_start",
            {"session_id": session_id, "tool": tool.name},
        )
        result = self._executor.execute(tool, request.get("payload", {}), retries=1, timeout_s=5)
        self._logger.info(
            "tool_execution_end",
            {"session_id": session_id, "tool": tool.name, "success": result.success},
        )
        return result
