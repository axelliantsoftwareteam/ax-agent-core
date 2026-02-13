from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    provider: str = "mock"
    fallback_order: list[str] | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    tool_timeout_s: float = 5.0
    tool_retries: int = 1
    tool_retry_backoff_s: float = 0.05
    log_level: str = "INFO"
    otel_enabled: bool = False


def load_config(path: str | None = None) -> AppConfig:
    file_data: dict[str, Any] = {}
    if path:
        with open(path, encoding="utf-8") as handle:
            file_data = json.load(handle)

    raw = {
        "provider": _env_or(file_data, "provider", "AX_AGENT_DEFAULT_PROVIDER", "mock"),
        "fallback_order": file_data.get("fallback_order"),
        "openai_api_key": _env_or(file_data, "openai_api_key", "AX_AGENT_OPENAI_API_KEY", None),
        "openai_model": _env_or(file_data, "openai_model", "AX_AGENT_OPENAI_MODEL", "gpt-4o-mini"),
        "tool_timeout_s": _env_or(file_data, "tool_timeout_s", "AX_AGENT_TOOL_TIMEOUT_S", 5.0),
        "tool_retries": _env_or(file_data, "tool_retries", "AX_AGENT_TOOL_RETRIES", 1),
        "tool_retry_backoff_s": _env_or(
            file_data,
            "tool_retry_backoff_s",
            "AX_AGENT_TOOL_RETRY_BACKOFF_S",
            0.05,
        ),
        "log_level": _env_or(file_data, "log_level", "AX_AGENT_LOG_LEVEL", "INFO"),
        "otel_enabled": _bool_env_or(file_data, "otel_enabled", "AX_AGENT_OTEL_ENABLED", False),
    }

    config = AppConfig(
        provider=str(raw["provider"]),
        fallback_order=list(raw["fallback_order"]) if raw["fallback_order"] else None,
        openai_api_key=raw["openai_api_key"],
        openai_model=str(raw["openai_model"]),
        tool_timeout_s=float(raw["tool_timeout_s"]),
        tool_retries=int(raw["tool_retries"]),
        tool_retry_backoff_s=float(raw["tool_retry_backoff_s"]),
        log_level=str(raw["log_level"]),
        otel_enabled=bool(raw["otel_enabled"]),
    )
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    if config.provider not in {"mock", "openai"}:
        raise ValueError("provider must be one of: mock, openai")
    if config.fallback_order is not None:
        allowed = {"mock", "openai"}
        invalid = [name for name in config.fallback_order if name not in allowed]
        if invalid:
            raise ValueError(f"fallback_order has unsupported provider(s): {invalid}")
    if config.tool_timeout_s <= 0:
        raise ValueError("tool_timeout_s must be > 0")
    if config.tool_retries < 0:
        raise ValueError("tool_retries must be >= 0")
    if config.tool_retry_backoff_s < 0:
        raise ValueError("tool_retry_backoff_s must be >= 0")


def _env_or(file_data: dict[str, Any], key: str, env_name: str, default: Any) -> Any:
    if env_name in os.environ and os.environ[env_name] != "":
        return os.environ[env_name]
    return file_data.get(key, default)


def _bool_env_or(file_data: dict[str, Any], key: str, env_name: str, default: bool) -> bool:
    if env_name in os.environ and os.environ[env_name] != "":
        return os.environ[env_name].strip().lower() in {"1", "true", "yes", "on"}
    value = file_data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
