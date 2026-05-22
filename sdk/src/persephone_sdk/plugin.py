from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping, Sequence, TypeVar

import numpy as np

from persephone_sdk.types import EventRecord, MetricRecord, SimulationFrame, StateDict

VALID_PARADIGMS = frozenset({"ode", "pde", "abm", "graph", "sde", "hybrid"})
VALID_ENTITY_FIELD_TYPES = frozenset(
    {"string", "integer", "number", "boolean", "categorical", "enum", "json"}
)
VALID_STATE_KINDS = frozenset({"categorical", "continuous", "ordinal", "boolean"})
VALID_METRIC_KINDS = frozenset({"scalar", "ratio", "delta", "index"})
VALID_VIEW_KINDS = frozenset(
    {"network", "positioned_graph", "map_network", "matrix", "table", "timeline", "heatmap", "hierarchy"}
)
VALID_EXPLANATION_SCOPES = frozenset({"run", "frame", "selection"})
T = TypeVar("T")


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

    def explain(
        self,
        state: StateDict,
        *,
        t: float,
        tick: int,
        run_id: str,
        solver_id: str,
        metrics: list[MetricRecord],
        events: list[EventRecord],
        frames: list[SimulationFrame],
    ) -> list[dict[str, Any]]:
        """Return deterministic explanation packets for the current step."""
        return []


class Renderer(ABC):
    """Provides read-only visualization hints."""

    @abstractmethod
    def viz_schema(self) -> dict[str, Any]:
        """Return a UI visualization schema."""

    def frame(
        self,
        state: StateDict,
        *,
        t: float,
        run_id: str,
        solver_id: str,
        tick: int,
        source: str = "live",
    ) -> list[SimulationFrame]:
        """Return normalized visualization frames for the current state."""
        return []


@dataclass
class EntityField:
    """Describes a human-facing field available on a plugin-defined entity schema."""

    name: str
    type: str
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    required: bool = False

    def __post_init__(self) -> None:
        _validate_required_text("entity field name", self.name)
        if self.type not in VALID_ENTITY_FIELD_TYPES:
            allowed = ", ".join(sorted(VALID_ENTITY_FIELD_TYPES))
            raise ValueError(f"entity field type must be one of: {allowed}")
        if self.label is not None:
            _validate_required_text("entity field label", self.label)


@dataclass
class StateDefinition:
    """Defines the meaning of a state channel emitted by a plugin."""

    name: str
    kind: str
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    values: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_required_text("state definition name", self.name)
        if self.kind not in VALID_STATE_KINDS:
            allowed = ", ".join(sorted(VALID_STATE_KINDS))
            raise ValueError(f"state definition kind must be one of: {allowed}")
        self.values = _normalize_string_list("state definition values", self.values)
        if self.label is not None:
            _validate_required_text("state definition label", self.label)


@dataclass
class MetricDefinition:
    """Defines a metric in terms the analysis UI can present directly."""

    name: str
    label: str | None = None
    kind: str = "scalar"
    description: str | None = None
    unit: str | None = None
    headline: bool = False

    def __post_init__(self) -> None:
        _validate_required_text("metric definition name", self.name)
        if self.kind not in VALID_METRIC_KINDS:
            allowed = ", ".join(sorted(VALID_METRIC_KINDS))
            raise ValueError(f"metric definition kind must be one of: {allowed}")
        if self.label is not None:
            _validate_required_text("metric definition label", self.label)


@dataclass
class EventDefinition:
    """Defines a named event and its human-facing interpretation."""

    name: str
    label: str | None = None
    description: str | None = None
    related_entity: str | None = None

    def __post_init__(self) -> None:
        _validate_required_text("event definition name", self.name)
        if self.label is not None:
            _validate_required_text("event definition label", self.label)
        if self.related_entity is not None:
            _validate_required_text("event related_entity", self.related_entity)


@dataclass
class ViewCapability:
    """Declares a reusable view mode the plugin can support."""

    kind: str
    label: str | None = None
    description: str | None = None
    default: bool = False
    requires_coordinates: bool = False

    def __post_init__(self) -> None:
        if self.kind not in VALID_VIEW_KINDS:
            allowed = ", ".join(sorted(VALID_VIEW_KINDS))
            raise ValueError(f"view capability kind must be one of: {allowed}")
        if self.label is not None:
            _validate_required_text("view capability label", self.label)


@dataclass
class ExplanationCapability:
    """Declares which explanation scopes a plugin can support deterministically."""

    scope: str
    label: str | None = None
    description: str | None = None
    fact_kinds: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.scope not in VALID_EXPLANATION_SCOPES:
            allowed = ", ".join(sorted(VALID_EXPLANATION_SCOPES))
            raise ValueError(f"explanation capability scope must be one of: {allowed}")
        self.fact_kinds = _normalize_string_list("explanation fact kinds", self.fact_kinds)
        if self.label is not None:
            _validate_required_text("explanation capability label", self.label)


@dataclass
class SemanticManifest:
    """Grouped semantic metadata for v4-capable plugins.

    All fields are optional so existing v3 plugins remain valid.
    """

    entity_schemas: dict[str, list[EntityField]] = field(default_factory=dict)
    state_schema: dict[str, StateDefinition] = field(default_factory=dict)
    metric_schema: dict[str, MetricDefinition] = field(default_factory=dict)
    event_schema: dict[str, EventDefinition] = field(default_factory=dict)
    view_capabilities: list[ViewCapability] = field(default_factory=list)
    explanation_capabilities: list[ExplanationCapability] = field(default_factory=list)
    default_entity_type: str | None = None
    preferred_view: str | None = None

    def __post_init__(self) -> None:
        self.entity_schemas = {
            _validated_mapping_key("entity schema key", key): _coerce_list(
                "entity schema fields",
                value,
                EntityField,
            )
            for key, value in self.entity_schemas.items()
        }
        self.state_schema = _coerce_mapping("state schema", self.state_schema, StateDefinition)
        self.metric_schema = _coerce_mapping("metric schema", self.metric_schema, MetricDefinition)
        self.event_schema = _coerce_mapping("event schema", self.event_schema, EventDefinition)
        self.view_capabilities = _coerce_list(
            "view capabilities", self.view_capabilities, ViewCapability
        )
        self.explanation_capabilities = _coerce_list(
            "explanation capabilities",
            self.explanation_capabilities,
            ExplanationCapability,
        )
        if self.default_entity_type is not None and self.default_entity_type not in self.entity_schemas:
            raise ValueError("default_entity_type must reference a declared entity schema")
        if self.preferred_view is not None and self.preferred_view not in {
            capability.kind for capability in self.view_capabilities
        }:
            raise ValueError("preferred_view must match one of the declared view capabilities")


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
    semantics: SemanticManifest = field(default_factory=SemanticManifest)
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
        self._normalize_semantics()

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

    def _normalize_semantics(self) -> None:
        self.semantics = _coerce_model("semantics", self.semantics, SemanticManifest)
        if not self.semantics.metric_schema and self.metrics_schema:
            self.semantics.metric_schema = {
                name: MetricDefinition(name=name, label=_humanize_identifier(name))
                for name in sorted(self.metrics_schema)
            }


def is_finite_state(state: StateDict) -> bool:
    return all(np.all(np.isfinite(value)) for value in state.values())


def _validate_required_text(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _validated_mapping_key(field_name: str, value: str) -> str:
    _validate_required_text(field_name, value)
    return value


def _normalize_string_list(field_name: str, values: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        _validate_required_text(field_name, value)
        normalized.append(value)
    return normalized


def _coerce_mapping(field_name: str, value: Mapping[str, object], model: type[T]) -> dict[str, T]:
    return {
        _validated_mapping_key(field_name, key): _coerce_model(field_name, item, model)
        for key, item in value.items()
    }


def _coerce_list(field_name: str, values: Sequence[object], model: type[T]) -> list[T]:
    return [_coerce_model(field_name, value, model) for value in values]


def _coerce_model(field_name: str, value: object, model: type[T]) -> T:
    if isinstance(value, model):
        return value
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} entries must be {model.__name__} or mappings")
    return model(**value)


def _humanize_identifier(value: str) -> str:
    return value.replace("_", " ").strip().title()
