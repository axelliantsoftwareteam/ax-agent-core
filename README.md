# ax-agent-core

Production-grade agentic AI core for tool-augmented agents with an MCP-ready interface layer, built by Axelliant Software Engineering.

- Website: `https://axelliant.com`
- General contact: `info@axelliant.com`
- Security contact: `security@axelliant.com`

## Overview

`ax-agent-core` provides a practical runtime foundation for building tool-using AI agents without locking into a single model provider or transport. It includes a runnable Ops Assistant demo, strict tool schema validation, retries/timeouts, provider fallback, memory, and observability hooks.

## Why this exists

Most agent demos are either toy-level or tightly coupled to one provider stack. This repository is designed as a clean, open-source core that teams can extend into production workflows with predictable behavior and clear interfaces.

## Features

- Agent runtime for handling conversational and tool-invocation flows.
- Tool registry with structured input schemas, runtime validation, retries, and timeouts.
- Model routing abstraction with pluggable providers.
- Built-in `MockProvider` and `OpenAIProvider` stub (no outbound calls).
- Conversation state and in-memory memory interface.
- Cost tracking interface with token/cost estimation stub.
- Structured JSON logging and optional OpenTelemetry span hooks.
- MCP-ready bridge for transport-agnostic tool listing and execution.
- CLI commands for demo run, tool discovery, and config validation.

## Architecture

```mermaid
flowchart LR
    U[User / CLI / API] --> A[Agent Runtime]
    A --> T[Tool Registry]
    T --> E[Tool Executor (schema, retry, timeout)]
    A --> R[Model Router]
    R --> P1[MockProvider]
    R --> P2[OpenAIProvider Stub]
    A --> M[Conversation Memory]
    A --> C[Cost Tracker]
    A --> O[Telemetry + Structured Logs]
    T --> B[MCP Bridge]
```

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
make setup
make demo
```

Run the interactive demo:

```bash
make run
```

## Configuration

Runtime config can come from JSON (`examples/config.json`) and/or environment variables.

### Supported environment variables

- `AX_AGENT_DEFAULT_PROVIDER`: `mock` or `openai`
- `AX_AGENT_OPENAI_API_KEY`: optional API key for future provider implementation
- `AX_AGENT_OPENAI_MODEL`: model ID string
- `AX_AGENT_TOOL_TIMEOUT_S`: per-tool timeout seconds
- `AX_AGENT_TOOL_RETRIES`: retry count
- `AX_AGENT_TOOL_RETRY_BACKOFF_S`: retry backoff seconds
- `AX_AGENT_LOG_LEVEL`: `DEBUG|INFO|WARNING|ERROR`
- `AX_AGENT_OTEL_ENABLED`: `true/false`

Use `.env.example` as the baseline and keep real secrets out of source control.

## API/CLI Usage

### CLI

```bash
ax-agent run-demo --scripted
ax-agent run-demo
ax-agent list-tools --config examples/config.json
ax-agent validate-config --config examples/config.json
```

### Python API

```python
from ax_agent_core.demo import build_demo_agent

agent = build_demo_agent("examples/config.json")
response = agent.runtime.handle('tool:math {"expression": "2+2"}', session_id="ops")
print(response.content)
print(response.tool_result.output)
```

MCP-ready bridge access:

```python
tools = agent.mcp_bridge.list_tools()
result = agent.mcp_bridge.call_tool("http_get", {"url": "https://status.axelliant.internal/health"})
```

## Examples

- `examples/demo.py`: runnable scripted demo.
- `examples/sample_prompts.txt`: realistic Ops Assistant prompts.
- `examples/config.json`: baseline config for local execution.

Run:

```bash
python examples/demo.py
```

## Testing

```bash
make test
```

Test coverage includes:

- Unit tests for tool execution, schema validation, timeout behavior.
- Unit tests for model routing fallback logic.
- Unit test for retry behavior on flaky tools.
- Integration smoke test for end-to-end Ops Assistant flow.

## Deployment (Docker)

Build image:

```bash
docker build -t ax-agent-core:latest .
```

Run scripted demo:

```bash
docker run --rm ax-agent-core:latest
```

Run with mounted config:

```bash
docker run --rm -v "$PWD/examples:/app/examples" ax-agent-core:latest validate-config --config examples/config.json
```

## Security notes

- Do not commit API keys or credentials.
- Validate all tool payloads with strict schemas (`additionalProperties: false` when possible).
- Use provider fallback to reduce single-provider outage risk.
- Review `SECURITY.md` for responsible disclosure policy.

## Roadmap

- Full OpenAI provider implementation behind explicit feature flag.
- Persistent memory backends (Redis/PostgreSQL adapters).
- First-class MCP transport server package.
- Policy engine for tool authorization and rate limits.
- Metrics exporter integrations (Prometheus/OpenTelemetry).

## Contributing

See `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` for development process and community standards.

## License

Licensed under Apache-2.0. See `LICENSE`.

---

Axelliant Software Engineering: `https://axelliant.com` | `info@axelliant.com` | `security@axelliant.com`
