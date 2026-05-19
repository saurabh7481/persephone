from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

import numpy as np

from persephone_sdk.types import EventRecord, MetricRecord, StateDict

VALID_PARADIGMS = frozenset({"ode", "pde", "abm", "graph", "sde", "hybrid"})


class World(ABC):
    """Defines simulation state shape and initialization."""

    @abstractmethod
    def schema(self) -> dict[str, tuple[int, ...]]:
        """Return state array shapes keyed by state name."""

    @abstractmethod
    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        """Return deterministic initial state for the given params and seed."""

    @abstractmethod
    def reset(self) -> StateDict:
        """Return the world to its initial state."""


class Solver(ABC):
    """Advances simulation state over one time interval."""

    @abstractmethod
    def step(self, state: StateDict, dt: float, bus: Any) -> tuple[StateDict, float]:
        """Advance state and return the elapsed time actually advanced."""

    @property
    @abstractmethod
    def preferred_dt(self) -> float:
        """Return the solver's preferred synchronization interval."""

    @property
    def is_stiff(self) -> bool:
        return False

    @property
    def is_stochastic(self) -> bool:
        return False


class Observer(ABC):
    """Emits metrics and events from committed simulation state."""

    @abstractmethod
    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        """Return metric records for the current state."""

    def on_event(self, event: str, payload: dict[str, Any], t: float) -> EventRecord | None:
        return None


class Renderer(ABC):
    """Provides read-only visualization hints."""

    @abstractmethod
    def viz_schema(self) -> dict[str, Any]:
        """Return a UI visualization schema."""


@dataclass
class PluginManifest:
    name: str
    version: str
    paradigm: str
    world: type[World]
    solver: type[Solver]
    observer: type[Observer]
    renderer: type[Renderer]
    bus_reads: list[str] = field(default_factory=list)
    bus_writes: list[str] = field(default_factory=list)
    default_params: dict[str, Any] = field(default_factory=dict)
    params_schema: dict[str, Any] = field(default_factory=dict)
    metrics_schema: dict[str, Any] = field(default_factory=dict)
    sdk_min_version: str = "0.1.0"

    _contracts: ClassVar[dict[str, type[Any]]] = {
        "world": World,
        "solver": Solver,
        "observer": Observer,
        "renderer": Renderer,
    }

    def __post_init__(self) -> None:
        self._validate_required_text("name", self.name)
        self._validate_required_text("version", self.version)
        self._validate_required_text("sdk_min_version", self.sdk_min_version)
        self._validate_paradigm()
        self._validate_contracts()

    def _validate_required_text(self, field_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")

    def _validate_paradigm(self) -> None:
        if self.paradigm not in VALID_PARADIGMS:
            allowed = ", ".join(sorted(VALID_PARADIGMS))
            raise ValueError(f"paradigm must be one of: {allowed}")

    def _validate_contracts(self) -> None:
        for field_name, expected_base in self._contracts.items():
            candidate = getattr(self, field_name)
            if not isinstance(candidate, type) or not issubclass(candidate, expected_base):
                raise TypeError(f"{field_name} must implement {expected_base.__name__}")


def is_finite_state(state: StateDict) -> bool:
    return all(np.all(np.isfinite(value)) for value in state.values())
