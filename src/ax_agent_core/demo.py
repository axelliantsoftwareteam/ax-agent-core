from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Dict

from .cost import StubCostTracker
from .memory import InMemoryConversationStore
from .observability import StructuredLogger
from .providers import MockProvider, OpenAIProvider, ModelRouter
from .runtime import AgentRuntime
from .tooling import ToolDefinition, ToolRegistry, pretty_json


@dataclass
class DemoAgent:
    runtime: AgentRuntime
    registry: ToolRegistry


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
    }

    def visit(self, node):
        if type(node) not in self._allowed_nodes:
            raise ValueError("Unsupported expression")
        return super().visit(node)

    def evaluate(self, expression: str) -> float:
        tree = ast.parse(expression, mode="eval")
        self.visit(tree)
        return self._eval_node(tree.body)

    def _eval_node(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numbers are allowed")
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
                return left ** right
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            if isinstance(node.op, ast.USub):
                return -operand
        raise ValueError("Unsupported expression")


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def math_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
        evaluator = SafeMathEvaluator()
        result = evaluator.evaluate(payload["expression"])
        return {"result": result}

    def http_get_stub(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": 200,
            "url": payload["url"],
            "body": "stubbed response",
        }

    def json_formatter(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"formatted": pretty_json(payload["payload"])}

    registry.register(
        ToolDefinition(
            name="math",
            description="Evaluate a simple math expression.",
            input_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
                "additionalProperties": False,
            },
            handler=math_tool,
        )
    )
    registry.register(
        ToolDefinition(
            name="http_get",
            description="Stubbed HTTP GET tool.",
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
                "additionalProperties": False,
            },
            handler=http_get_stub,
        )
    )
    registry.register(
        ToolDefinition(
            name="json_formatter",
            description="Format JSON payload.",
            input_schema={
                "type": "object",
                "properties": {"payload": {"type": "object"}},
                "required": ["payload"],
                "additionalProperties": False,
            },
            handler=json_formatter,
        )
    )
    return registry


def build_demo_agent() -> DemoAgent:
    registry = build_registry()
    router = ModelRouter([MockProvider(), OpenAIProvider()])
    memory = InMemoryConversationStore()
    cost_tracker = StubCostTracker()
    logger = StructuredLogger("ax_agent_core.demo")
    runtime = AgentRuntime(
        registry=registry,
        router=router,
        memory=memory,
        cost_tracker=cost_tracker,
        logger=logger,
    )
    return DemoAgent(runtime=runtime, registry=registry)


def run_demo() -> None:
    agent = build_demo_agent()
    print("Ops Assistant demo. Try: tool:math {\"expression\": \"2+2\"}")
    print("Type 'exit' to quit.")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        response = agent.runtime.handle(user_input)
        print(response.content)
