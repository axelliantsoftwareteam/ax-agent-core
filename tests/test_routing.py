from ax_agent_core.providers import ModelRouter, ProviderError, ProviderResponse


class FailingProvider:
    name = "fail"

    def generate(self, prompt: str) -> ProviderResponse:
        raise ProviderError("boom")


class SucceedingProvider:
    name = "ok"

    def generate(self, prompt: str) -> ProviderResponse:
        return ProviderResponse(text="ok", provider=self.name, usage={"tokens": 1})


def test_routing_fallback():
    router = ModelRouter([FailingProvider(), SucceedingProvider()])
    response = router.generate("hello")
    assert response.text == "ok"
    assert response.provider == "ok"
