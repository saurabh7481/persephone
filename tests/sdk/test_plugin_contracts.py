from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest
from persephone_heat_diffusion import HeatDiffusionPlugin
from persephone_sdk.plugin import (
    ExplanationCapability,
    Observer,
    PluginManifest,
    Renderer,
    SemanticManifest,
    Solver,
    ViewCapability,
    World,
)
from persephone_sdk.testing import PluginTestHarness


class DemoWorld(World):
    def __init__(self) -> None:
        self._initial: dict[str, np.ndarray] | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        return {"population": (3,)}

    def init(self, params: dict[str, Any], seed: int) -> dict[str, np.ndarray]:
        self._initial = {"population": np.array([1.0, 2.0, 3.0])}
        return {key: value.copy() for key, value in self._initial.items()}

    def reset(self) -> dict[str, np.ndarray]:
        assert self._initial is not None
        return {key: value.copy() for key, value in self._initial.items()}


class DemoSolver(Solver):
    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(
        self, state: dict[str, np.ndarray], dt: float, bus: Any
    ) -> tuple[dict[str, np.ndarray], float]:
        bus.write("population", state["population"], solver_id="demo", tick=1)
        return {"population": state["population"] + dt}, dt


class DemoObserver(Observer):
    def observe(self, state: dict[str, np.ndarray], t: float, run_id: str) -> list[dict[str, Any]]:
        return [
            {
                "metric": "population_sum",
                "value": float(state["population"].sum()),
                "t": t,
                "tags": {"run_id": run_id},
            }
        ]


class DemoRenderer(Renderer):
    def viz_schema(self) -> dict[str, str]:
        return {"type": "line"}


def demo_manifest() -> PluginManifest:
    return PluginManifest(
        name="demo",
        version="0.1.0",
        paradigm="ode",
        world=DemoWorld,
        solver=DemoSolver,
        observer=DemoObserver,
        renderer=DemoRenderer,
        bus_reads=[],
        bus_writes=["population"],
        default_params={},
        params_schema={"type": "object"},
        metrics_schema={"population_sum": {"type": "number"}},
        sdk_min_version="0.1.0",
    )


class DemoPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return demo_manifest()


@dataclass
class NotAWorld:
    value: int = 1


def test_manifest_rejects_classes_that_do_not_implement_contracts() -> None:
    with pytest.raises(TypeError, match="world"):
        PluginManifest(
            name="bad",
            version="0.1.0",
            paradigm="ode",
            world=NotAWorld,
            solver=DemoSolver,
            observer=DemoObserver,
            renderer=DemoRenderer,
            bus_reads=[],
            bus_writes=[],
            default_params={},
            params_schema={},
            metrics_schema={},
            sdk_min_version="0.1.0",
        )


def test_manifest_rejects_unknown_paradigm() -> None:
    with pytest.raises(ValueError, match="paradigm"):
        PluginManifest(
            name="bad",
            version="0.1.0",
            paradigm="spreadsheet",
            world=DemoWorld,
            solver=DemoSolver,
            observer=DemoObserver,
            renderer=DemoRenderer,
            bus_reads=[],
            bus_writes=[],
            default_params={},
            params_schema={},
            metrics_schema={},
            sdk_min_version="0.1.0",
        )


def test_plugin_harness_accepts_compliant_plugin() -> None:
    PluginTestHarness(DemoPlugin).run_all()


class UndeclaredWriteSolver(DemoSolver):
    def step(
        self, state: dict[str, np.ndarray], dt: float, bus: Any
    ) -> tuple[dict[str, np.ndarray], float]:
        bus.write("undeclared", state["population"], solver_id="demo", tick=1)
        return state, dt


class BadPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        manifest = demo_manifest()
        manifest.solver = UndeclaredWriteSolver
        manifest.bus_writes = ["population"]
        return manifest


def test_plugin_harness_rejects_undeclared_bus_writes() -> None:
    with pytest.raises(AssertionError, match="undeclared"):
        PluginTestHarness(BadPlugin).run_all()


class UndeclaredReadSolver(DemoSolver):
    def step(
        self, state: dict[str, np.ndarray], dt: float, bus: Any
    ) -> tuple[dict[str, np.ndarray], float]:
        bus.read("undeclared_input")
        return state, dt


class BadReadPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        manifest = demo_manifest()
        manifest.solver = UndeclaredReadSolver
        manifest.bus_reads = ["declared_input"]
        return manifest


def test_plugin_harness_rejects_undeclared_bus_reads() -> None:
    with pytest.raises(AssertionError, match="undeclared_input"):
        PluginTestHarness(BadReadPlugin).run_all()


def test_manifest_normalizes_nested_semantic_contracts() -> None:
    manifest = PluginManifest(
        name="semantic-demo",
        version="0.1.0",
        paradigm="graph",
        world=DemoWorld,
        solver=DemoSolver,
        observer=DemoObserver,
        renderer=DemoRenderer,
        bus_reads=[],
        bus_writes=["population"],
        metrics_schema={"population_sum": {"type": "number"}},
        semantics=SemanticManifest(
            entity_schemas={
                "node": [
                    {
                        "name": "population",
                        "type": "number",
                        "label": "Population",
                        "required": True,
                    }
                ]
            },
            state_schema={
                "population": {
                    "name": "population",
                    "kind": "continuous",
                    "label": "Population",
                }
            },
            metric_schema={
                "population_sum": {
                    "name": "population_sum",
                    "label": "Population sum",
                    "unit": "people",
                }
            },
            event_schema={
                "population_changed": {
                    "name": "population_changed",
                    "label": "Population changed",
                }
            },
            view_capabilities=[
                {"kind": "network", "label": "Network", "default": True},
                {"kind": "table", "label": "Table"},
            ],
            explanation_capabilities=[
                {
                    "scope": "run",
                    "label": "Run summary",
                    "fact_kinds": ["trend", "milestone"],
                }
            ],
            preferred_view="network",
        ),
        sdk_min_version="0.1.0",
    )

    assert manifest.semantics.entity_schemas["node"][0].name == "population"
    assert manifest.semantics.metric_schema["population_sum"].unit == "people"
    assert manifest.semantics.view_capabilities[0] == ViewCapability(
        kind="network",
        label="Network",
        default=True,
    )
    assert manifest.semantics.explanation_capabilities[0] == ExplanationCapability(
        scope="run",
        label="Run summary",
        fact_kinds=["trend", "milestone"],
    )


def test_manifest_derives_minimal_metric_semantics_from_existing_metrics_schema() -> None:
    manifest = demo_manifest()

    assert manifest.semantics.metric_schema["population_sum"].name == "population_sum"
    assert manifest.semantics.metric_schema["population_sum"].kind == "scalar"


def test_manifest_rejects_invalid_semantic_capabilities() -> None:
    with pytest.raises(ValueError, match="preferred_view"):
        PluginManifest(
            name="bad-semantics",
            version="0.1.0",
            paradigm="graph",
            world=DemoWorld,
            solver=DemoSolver,
            observer=DemoObserver,
            renderer=DemoRenderer,
            bus_reads=[],
            bus_writes=["population"],
            metrics_schema={"population_sum": {"type": "number"}},
            semantics=SemanticManifest(
                view_capabilities=[{"kind": "network"}],
                preferred_view="heatmap",
            ),
            sdk_min_version="0.1.0",
        )


def test_heat_diffusion_plugin_demonstrates_non_spatial_semantics() -> None:
    manifest = HeatDiffusionPlugin.manifest()

    assert manifest.semantics.preferred_view == "heatmap"
    assert manifest.semantics.state_schema["temperature"].kind == "continuous"
    assert [capability.kind for capability in manifest.semantics.view_capabilities] == [
        "heatmap",
        "table",
    ]
