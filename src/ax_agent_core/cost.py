from __future__ import annotations

from typing import Dict, Protocol


class CostTracker(Protocol):
    def record(self, usage: Dict[str, float]) -> None:
        ...

    def totals(self) -> Dict[str, float]:
        ...


class StubCostTracker:
    def __init__(self) -> None:
        self._totals = {"tokens": 0.0, "cost": 0.0}

    def record(self, usage: Dict[str, float]) -> None:
        for key, value in usage.items():
            self._totals[key] = self._totals.get(key, 0.0) + float(value)

    def totals(self) -> Dict[str, float]:
        return dict(self._totals)
