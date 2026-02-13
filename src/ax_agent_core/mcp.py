from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .tooling import ToolExecutionPolicy, ToolExecutor, ToolRegistry


@dataclass(frozen=True)
class MCPToolDescriptor:
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPBridge:
    """MCP-ready bridge exposing tool metadata and invocation primitives.

    This class is transport-agnostic by design. It can be mounted behind stdin,
    HTTP, WebSocket, or native MCP server adapters without changing tool logic.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        executor: Optional[ToolExecutor] = None,
        policy: Optional[ToolExecutionPolicy] = None,
    ) -> None:
        self._registry = registry
        self._executor = executor or ToolExecutor()
        self._policy = policy or ToolExecutionPolicy()

    def list_tools(self) -> List[MCPToolDescriptor]:
        return [
            MCPToolDescriptor(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
            )
            for tool in self._registry.list()
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._registry.get(name)
        result = self._executor.execute(tool, arguments, self._policy)
        return {
            "tool": name,
            "success": result.success,
            "attempts": result.attempts,
            "duration_ms": result.duration_ms,
            "output": result.output,
            "error": result.error,
        }

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "tool_count": len(self._registry.list()),
            "mcp_ready": True,
        }
