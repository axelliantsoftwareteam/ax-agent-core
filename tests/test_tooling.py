from ax_agent_core.demo import build_registry
from ax_agent_core.tooling import ToolExecutor, ToolSchemaValidator


def test_tool_execution_success():
    registry = build_registry()
    tool = registry.get("math")
    executor = ToolExecutor()
    result = executor.execute(tool, {"expression": "2+2"})
    assert result.success is True
    assert result.output["result"] == 4


def test_schema_validation_missing_field():
    registry = build_registry()
    tool = registry.get("math")
    validator = ToolSchemaValidator()
    try:
        validator.validate(tool.input_schema, {})
    except Exception as exc:
        assert "Missing required field" in str(exc)
    else:
        raise AssertionError("Expected schema validation error")
