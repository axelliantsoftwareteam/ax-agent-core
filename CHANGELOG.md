# Changelog

All notable changes to this project are documented in this file.

## 0.1.0 - 2026-02-13

### Added
- Production-ready MVP agent runtime with tool registry, schema validation, retries, and timeouts.
- Provider routing layer with fallback behavior, `MockProvider`, and `OpenAIProvider` stub.
- In-memory conversation state and cost-tracking interfaces.
- Structured JSON logging and optional OpenTelemetry hooks.
- MCP-ready bridge interface for tool discovery and invocation.
- CLI commands: `run-demo`, `list-tools`, `validate-config`.
- Ops Assistant demo tools: `math`, `http_get`, `json_formatter`.
- Unit and smoke tests for tooling, routing, retry behavior, and runtime integration.
- Dockerfile, Makefile, CI workflows, and repository hygiene documentation.
