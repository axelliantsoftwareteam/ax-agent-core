from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


class ProviderError(RuntimeError):
    pass


@dataclass
class ProviderResponse:
    text: str
    provider: str
    usage: Dict[str, Any]


class Provider(Protocol):
    name: str

    def generate(self, prompt: str) -> ProviderResponse:
        ...


class MockProvider:
    name = "mock"

    def generate(self, prompt: str) -> ProviderResponse:
        tokens = max(1, len(prompt) // 4)
        return ProviderResponse(
            text=f"[mock] Echo: {prompt}",
            provider=self.name,
            usage={"tokens": tokens, "cost": 0.0},
        )


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str) -> ProviderResponse:
        raise ProviderError(
            "OpenAIProvider is a stub. Configure a real client in production."
        )


class ModelRouter:
    def __init__(self, providers: List[Provider], fallback_order: Optional[List[str]] = None) -> None:
        if not providers:
            raise ValueError("At least one provider must be configured")
        self._providers = {provider.name: provider for provider in providers}
        self._fallback_order = fallback_order or [provider.name for provider in providers]

    def generate(self, prompt: str, provider_name: Optional[str] = None) -> ProviderResponse:
        if provider_name:
            provider = self._providers.get(provider_name)
            if not provider:
                raise ProviderError(f"Unknown provider: {provider_name}")
            return provider.generate(prompt)

        last_error: Optional[Exception] = None
        for name in self._fallback_order:
            provider = self._providers.get(name)
            if provider is None:
                continue
            try:
                return provider.generate(prompt)
            except Exception as exc:
                last_error = exc
                continue
        raise ProviderError("All providers failed") from last_error
