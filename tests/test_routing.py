from __future__ import annotations

from ax_agent_core.providers import ModelRouter, ProviderError, ProviderRequest, ProviderResponse


class FailingProvider:
    name = "fail"

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise ProviderError(f"forced failure for: {request.prompt}")


class SucceedingProvider:
    name = "ok"

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(
            text=f"ok:{request.prompt}",
            provider=self.name,
            usage={"tokens": 1.0, "cost": 0.0},
        )


def test_routing_fallback() -> None:
    router = ModelRouter([FailingProvider(), SucceedingProvider()], fallback_order=["fail", "ok"])
    response = router.generate(ProviderRequest(prompt="hello"))
    assert response.provider == "ok"
    assert response.text == "ok:hello"
    assert "fallback_errors" in response.metadata


def test_unknown_explicit_provider_fails() -> None:
    router = ModelRouter([SucceedingProvider()])
    try:
        router.generate(ProviderRequest(prompt="hello"), provider_name="missing")
    except ProviderError as exc:
        assert "unknown provider" in str(exc)
    else:
        raise AssertionError("expected ProviderError")
