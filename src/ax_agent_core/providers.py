from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Raised when a model provider cannot complete generation."""


@dataclass(frozen=True)
class ProviderRequest:
    prompt: str
    system_prompt: str | None = None
    max_tokens: int = 256
    temperature: float = 0.0


@dataclass
class ProviderResponse:
    text: str
    provider: str
    usage: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    name: str

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        ...


class MockProvider:
    """Deterministic provider used for local development and tests."""

    name = "mock"

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        prompt = request.prompt.strip()
        if not prompt:
            raise ProviderError("empty prompt")
        prompt_tokens = max(1, len(prompt.split()))
        completion_tokens = min(64, max(4, len(prompt) // 8))
        total_tokens = prompt_tokens + completion_tokens
        return ProviderResponse(
            text=f"[mock:{prompt_tokens}] {prompt}",
            provider=self.name,
            usage={
                "input_tokens": float(prompt_tokens),
                "output_tokens": float(completion_tokens),
                "tokens": float(total_tokens),
                "cost": 0.0,
            },
            metadata={"model": "mock-local-v1"},
        )


class OpenAIProvider:
    """Stub provider for OpenAI routing integration.

    This implementation intentionally avoids real API calls so the repository is
    runnable in any environment without external dependencies.
    """

    name = "openai"

    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise ProviderError(
            "OpenAIProvider stub is configured, but outbound API calls are disabled in this MVP. "
            "Use provider=mock for runnable local demos."
        )


class ModelRouter:
    def __init__(
        self,
        providers: list[Provider],
        fallback_order: list[str] | None = None,
    ) -> None:
        if not providers:
            raise ValueError("at least one provider must be configured")
        provider_map = {provider.name: provider for provider in providers}
        if len(provider_map) != len(providers):
            raise ValueError("provider names must be unique")

        self._providers = provider_map
        self._fallback_order = fallback_order or list(provider_map.keys())
        if not self._fallback_order:
            raise ValueError("fallback order must not be empty")

    @property
    def providers(self) -> list[str]:
        return list(self._providers.keys())

    def generate(
        self,
        request: ProviderRequest,
        provider_name: str | None = None,
    ) -> ProviderResponse:
        if provider_name is not None:
            provider = self._providers.get(provider_name)
            if provider is None:
                raise ProviderError(f"unknown provider: {provider_name}")
            try:
                return provider.generate(request)
            except ProviderError:
                raise
            except Exception as exc:
                raise ProviderError(f"provider '{provider_name}' failed: {exc}") from exc

        errors: dict[str, str] = {}
        for candidate in self._fallback_order:
            provider = self._providers.get(candidate)
            if provider is None:
                continue
            try:
                response = provider.generate(request)
                if errors:
                    response.metadata["fallback_errors"] = errors
                return response
            except ProviderError as exc:
                errors[candidate] = str(exc)
            except Exception as exc:
                errors[candidate] = f"{type(exc).__name__}: {exc}"

        raise ProviderError(f"all providers failed: {errors}")
