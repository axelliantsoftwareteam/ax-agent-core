from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Dict, Protocol


class CostTracker(Protocol):
    def record(self, usage: Dict[str, float]) -> None:
        ...

    def totals(self) -> Dict[str, float]:
        ...

    def estimate(self, text: str) -> Dict[str, float]:
        ...


@dataclass(frozen=True)
class CostModel:
    input_cost_per_1k_tokens: float = 0.0
    output_cost_per_1k_tokens: float = 0.0


class StubCostTracker:
    """Tracks observed usage and provides coarse token/cost estimates."""

    def __init__(self, model: CostModel | None = None) -> None:
        self._model = model or CostModel()
        self._totals: Dict[str, float] = {
            "input_tokens": 0.0,
            "output_tokens": 0.0,
            "tokens": 0.0,
            "cost": 0.0,
        }
        self._lock = RLock()

    def record(self, usage: Dict[str, float]) -> None:
        with self._lock:
            for key, value in usage.items():
                self._totals[key] = self._totals.get(key, 0.0) + float(value)

    def totals(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._totals)

    def estimate(self, text: str) -> Dict[str, float]:
        tokens = max(1, int(len(text) / 4))
        input_cost = (tokens / 1000.0) * self._model.input_cost_per_1k_tokens
        return {
            "input_tokens": float(tokens),
            "output_tokens": 0.0,
            "tokens": float(tokens),
            "cost": float(input_cost),
        }
