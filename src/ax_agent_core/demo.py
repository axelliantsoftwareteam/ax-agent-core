from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .config import AppConfig, load_config
from .cost import StubCostTracker
from .mcp import MCPBridge
from .memory import InMemoryConversationStore
from .observability import OpenTelemetryHook, StructuredLogger
from .providers import MockProvider, ModelRouter, OpenAIProvider
from .runtime import AgentRuntime
from .tooling import ToolDefinition, ToolExecutionPolicy, ToolRegistry, pretty_json


@dataclass
class DemoAgent:
    runtime: AgentRuntime
    mcp_bridge: MCPBridge


class SafeMathEvaluator(ast.NodeVisitor):
    _allowed_nodes = {
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Constant,
        ast.Load,
    }

    def visit(self, node: ast.AST) -> Any:
        if type(node) not in self._allowed_nodes:
            raise ValueError("unsupported expression")
        return super().visit(node)

    def evaluate(self, expression: str) -> float:
        parsed = ast.parse(expression, mode="eval")
        self.visit(parsed)
        return float(self._eval_node(parsed.body))

    def _eval_node(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError("only numeric constants are allowed")

        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.Pow):
                return left**right

        if isinstance(node, ast.UnaryOp):
            value = self._eval_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +value
            if isinstance(node.op, ast.USub):
                return -value

        raise ValueError("unsupported expression")


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def math_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
        evaluator = SafeMathEvaluator()
        result = evaluator.evaluate(payload["expression"])
        return {"result": result}

    def http_get_stub(payload: Dict[str, Any]) -> Dict[str, Any]:
        url = payload["url"]
        status = 200
        if "error" in url:
            status = 503
        return {
            "status": status,
            "url": url,
            "headers": {"content-type": "application/json"},
            "body": {"service": "http_get_stub", "healthy": status == 200},
        }

    def json_formatter(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"formatted": pretty_json(payload["payload"])}

    registry.register(
        ToolDefinition(
            name="math",
            description="Evaluate safe arithmetic expressions.",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "minLength": 1},
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
            handler=math_tool,
        )
    )

    registry.register(
        ToolDefinition(
            name="http_get",
            description="HTTP GET stub for deterministic demos and tests.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "minLength": 4},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            handler=http_get_stub,
        )
    )

    registry.register(
        ToolDefinition(
            name="json_formatter",
            description="Pretty-print a JSON object payload.",
            input_schema={
                "type": "object",
                "properties": {
                    "payload": {"type": "object"},
                },
                "required": ["payload"],
                "additionalProperties": False,
            },
            handler=json_formatter,
        )
    )

    return registry


def _build_router(config: AppConfig) -> ModelRouter:
    providers = [
        MockProvider(),
        OpenAIProvider(api_key=config.openai_api_key, model=config.openai_model),
    ]
    if config.fallback_order:
        fallback_order = config.fallback_order
    else:
        all_names = ["mock", "openai"]
        fallback_order = [config.provider] + [name for name in all_names if name != config.provider]
    return ModelRouter(providers=providers, fallback_order=fallback_order)


def build_demo_agent(config_path: Optional[str] = None) -> DemoAgent:
    config = load_config(config_path)
    registry = build_registry()

    runtime = AgentRuntime(
        registry=registry,
        router=_build_router(config),
        memory=InMemoryConversationStore(),
        cost_tracker=StubCostTracker(),
        logger=StructuredLogger("ax_agent_core.demo", level=config.log_level),
        telemetry=OpenTelemetryHook(enabled=config.otel_enabled),
        execution_policy=ToolExecutionPolicy(
            retries=config.tool_retries,
            timeout_s=config.tool_timeout_s,
            retry_backoff_s=config.tool_retry_backoff_s,
        ),
    )

    bridge = MCPBridge(
        registry=registry,
        policy=ToolExecutionPolicy(
            retries=config.tool_retries,
            timeout_s=config.tool_timeout_s,
            retry_backoff_s=config.tool_retry_backoff_s,
        ),
    )

    return DemoAgent(runtime=runtime, mcp_bridge=bridge)


def default_scripted_prompts() -> List[str]:
    return [
        'tool:math {"expression": "(12 / 3) + 7"}',
        'tool:http_get {"url": "https://status.axelliant.internal/health"}',
        'tool:json_formatter {"payload": {"service": "agent-core", "state": "ok"}}',
        "summarize current system status",
    ]


def run_demo(scripted: bool = False, prompts: Optional[Iterable[str]] = None) -> None:
    agent = build_demo_agent()

    if scripted:
        for prompt in list(prompts or default_scripted_prompts()):
            response = agent.runtime.handle(prompt, session_id="ops-demo")
            print(f"User: {prompt}")
            print(f"Assistant: {response.content}")
            if response.tool_result and response.tool_result.output is not None:
                print(f"Tool Output: {response.tool_result.output}")
            print("-")
        return

    print("Ops Assistant Demo")
    print("Commands: tool:<name> {json}, 'history' for guidance, 'exit' to quit")
    sample_prompts_path = Path("examples/sample_prompts.txt")

    while True:
        user_input = input("> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if user_input.lower() == "history" and sample_prompts_path.exists():
            print(sample_prompts_path.read_text(encoding="utf-8"))
            continue

        response = agent.runtime.handle(user_input, session_id="ops-demo")
        print(response.content)
        if response.tool_result and response.tool_result.output is not None:
            print(pretty_json(response.tool_result.output))
