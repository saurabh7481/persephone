from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

CouplingMerge = Callable[[NDArray[np.generic]], NDArray[np.generic]]


class CouplingRuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, CouplingMerge] = {}

    def register(self, name: str, merge: CouplingMerge) -> None:
        if not name.strip():
            raise ValueError("Coupling rule name cannot be empty")
        self._rules[name] = merge

    def has(self, name: str) -> bool:
        return name in self._rules

    def resolve(self, name: str) -> CouplingMerge:
        try:
            return self._rules[name]
        except KeyError as exc:
            raise ValueError(f"Unknown coupling rule: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._rules)


coupling_registry = CouplingRuleRegistry()
coupling_registry.register("sum", lambda values: values.sum(axis=0))
coupling_registry.register("mean", lambda values: values.mean(axis=0))
coupling_registry.register("max", lambda values: values.max(axis=0))
coupling_registry.register("min", lambda values: values.min(axis=0))
coupling_registry.register("last", lambda values: values[-1])
