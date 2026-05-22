from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

import numpy as np
from fastapi.testclient import TestClient
from persephone_sdk.plugin import (
    ExplanationCapability,
    MetricDefinition,
    Observer,
    PluginManifest,
    Renderer,
    SemanticManifest,
    Solver,
    ViewCapability,
    World,
)

from persephone.api.app import create_app
from persephone.config.models import ExperimentConfig, SchedulerConfig, SolverConfig
from persephone.core.engine import PersephoneEngine
from persephone.core.interpretation import InterpretationService
from persephone.registry.registry import PluginRegistry


class ExplanationWorld(World):
    def __init__(self) -> None:
        self._initial: dict[str, np.ndarray] | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        return {"population": (1,)}

    def init(self, params: dict[str, Any], seed: int) -> dict[str, np.ndarray]:
        self._initial = {"population": np.array([1.0], dtype=np.float64)}
        return {"population": self._initial["population"].copy()}

    def reset(self) -> dict[str, np.ndarray]:
        assert self._initial is not None
        return {"population": self._initial["population"].copy()}


class ExplanationSolver(Solver):
    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(
        self, state: dict[str, np.ndarray], dt: float, bus: Any
    ) -> tuple[dict[str, np.ndarray], float]:
        return {"population": state["population"] + dt}, dt


class ExplanationObserver(Observer):
    def observe(self, state: dict[str, np.ndarray], t: float, run_id: str) -> list[dict[str, Any]]:
        return [
            {
                "run_id": run_id,
                "solver_id": "explain#0",
                "metric": "population_sum",
                "value": float(state["population"].sum()),
                "t": t,
                "tags": {},
            }
        ]

    def explain(
        self,
        state: dict[str, np.ndarray],
        *,
        t: float,
        tick: int,
        run_id: str,
        solver_id: str,
        metrics: list[dict[str, Any]],
        events: list[dict[str, Any]],
        frames: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        assert not events
        return [
            {
                "scope": "run",
                "facts": [
                    {
                        "kind": "trend",
                        "title": "Population is rising",
                        "summary": "Population increased above the initial baseline.",
                        "severity": "warning",
                        "evidence": [{"label": "population_sum", "value": metrics[0]["value"]}],
                        "related_ids": ["population"],
                        "t": t,
                    }
                ],
            },
            {
                "scope": "frame",
                "frame_id": frames[0]["frame_id"],
                "facts": [
                    {
                        "kind": "milestone",
                        "title": "Frame captured",
                        "summary": "A graph frame was emitted for interpretation.",
                        "severity": "info",
                        "evidence": [{"label": "frame_id", "value": frames[0]["frame_id"]}],
                        "related_ids": ["frame"],
                        "t": t,
                    }
                ],
            },
            {
                "scope": "selection",
                "selection_id": "population",
                "facts": [
                    {
                        "kind": "selection",
                        "title": "Population selection",
                        "summary": "The population entity is available for focused inspection.",
                        "severity": "info",
                        "evidence": [{"label": "solver_id", "value": solver_id}],
                        "related_ids": ["population"],
                        "t": t,
                    }
                ],
            },
        ]


class ExplanationRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {"type": "graph"}

    def frame(
        self,
        state: dict[str, np.ndarray],
        *,
        t: float,
        run_id: str,
        solver_id: str,
        tick: int,
        source: str = "live",
    ) -> list[dict[str, Any]]:
        return [
            {
                "kind": "graph",
                "run_id": run_id,
                "frame_id": f"{solver_id}:graph:{tick:06d}",
                "t": t,
                "tick": tick,
                "solver_id": solver_id,
                "source": source,
                "nodes": [{"id": "population", "label": "Population", "state": "active"}],
                "edges": [],
                "visualization": {"preferred_view": "table"},
            }
        ]


class StaticRegistry(PluginRegistry):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(entry_points_provider=lambda: [])
        self._manifest = manifest

    def discover(self) -> None:
        self._plugins = {"explain": self._manifest}
        self.load_errors = {}


def explanation_manifest() -> PluginManifest:
    return PluginManifest(
        name="explain",
        version="0.1.0",
        paradigm="graph",
        world=ExplanationWorld,
        solver=ExplanationSolver,
        observer=ExplanationObserver,
        renderer=ExplanationRenderer,
        bus_reads=[],
        bus_writes=["population"],
        semantics=SemanticManifest(
            metric_schema={
                "population_sum": MetricDefinition(
                    name="population_sum",
                    label="Population sum",
                    headline=True,
                )
            },
            view_capabilities=[
                ViewCapability(kind="table", default=True),
                ViewCapability(kind="timeline"),
            ],
            explanation_capabilities=[
                ExplanationCapability(scope="run", label="Run summary"),
                ExplanationCapability(scope="frame", label="Frame summary"),
                ExplanationCapability(scope="selection", label="Selection summary"),
            ],
            preferred_view="table",
        ),
    )


def explanation_config(mode: str) -> ExperimentConfig:
    return ExperimentConfig(
        name="explain",
        seed=7,
        scheduler=SchedulerConfig(t_end=1.0, sync_interval=1.0),
        solvers=[SolverConfig(type="graph", plugin="explain", version=">=0.1.0")],
        observer={"emit_every": 1.0},
        visualization={"emit_every": 1.0},
        interpretation={
            "mode": mode,
            "every_n_ticks": 1,
            "on_milestone": True,
            "on_complete": True,
            "max_input_facts": 1,
            "max_output_tokens": 10,
            "store_records": True,
        },
    )


def create_explanation_run(tmp_path: Path, *, mode: str, run_id: str) -> str:
    PersephoneEngine(
        registry=StaticRegistry(explanation_manifest()),
        artifact_root=tmp_path / "runs",
    ).run(explanation_config(mode), run_id=run_id)
    return run_id


def test_api_exposes_plugin_semantics_and_scope_specific_explanations(tmp_path: Path) -> None:
    run_id = create_explanation_run(tmp_path, mode="rules_only", run_id="api-explain-run")
    app = create_app(artifact_root=tmp_path / "runs")
    app.state.plugin_registry = StaticRegistry(explanation_manifest())
    client = TestClient(app)

    semantics = client.get("/plugins/explain/semantics")
    run = client.get(f"/runs/{run_id}")
    frames = client.get(f"/runs/{run_id}/frames")
    frame_id = frames.json()["frames"][0]["frame_id"]
    run_explanation = client.get(f"/runs/{run_id}/explanations/run")
    frame_explanation = client.get(f"/runs/{run_id}/frames/{quote(frame_id, safe='')}/explanation")
    selection_explanation = client.get(f"/runs/{run_id}/selections/population/explanation")

    assert semantics.status_code == 200
    assert semantics.json()["semantics"]["preferred_view"] == "table"
    assert run.status_code == 200
    assert run.json()["plugin_semantics"][0]["semantics"]["preferred_view"] == "table"
    assert run_explanation.status_code == 200
    assert run_explanation.json()["available"] is True
    assert run_explanation.json()["interpretation"]["mode_applied"] == "rules_only"
    assert frame_explanation.json()["interpretation"]["scope"] == "frame"
    assert selection_explanation.json()["interpretation"]["scope"] == "selection"


def test_api_reports_missing_explanation_support_for_unknown_selection(tmp_path: Path) -> None:
    run_id = create_explanation_run(tmp_path, mode="rules_only", run_id="api-explain-missing")
    app = create_app(artifact_root=tmp_path / "runs")
    app.state.plugin_registry = StaticRegistry(explanation_manifest())
    client = TestClient(app)

    response = client.get(f"/runs/{run_id}/selections/unknown/explanation")

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert "No explanation facts" in response.json()["reason"]


def test_api_reuses_cached_minimal_ai_interpretations(tmp_path: Path) -> None:
    run_id = create_explanation_run(tmp_path, mode="minimal_ai", run_id="api-explain-ai")
    calls: list[dict[str, object]] = []

    def fake_ai(prompt: dict[str, object]) -> str:
        calls.append(prompt)
        return "Population remains above baseline with a sustained increase over the initial state"

    app = create_app(artifact_root=tmp_path / "runs")
    app.state.plugin_registry = StaticRegistry(explanation_manifest())
    app.state.interpretation_service = InterpretationService(
        tmp_path / "runs",
        ai_paraphraser=fake_ai,
    )
    client = TestClient(app)

    first = client.get(f"/runs/{run_id}/explanations/run")
    second = client.get(f"/runs/{run_id}/explanations/run")

    assert first.status_code == 200
    assert first.json()["interpretation"]["cached"] is False
    assert second.json()["interpretation"]["cached"] is True
    assert len(calls) == 1


def test_api_surfaces_disabled_interpretation_mode_cleanly(tmp_path: Path) -> None:
    run_id = create_explanation_run(tmp_path, mode="off", run_id="api-explain-off")
    app = create_app(artifact_root=tmp_path / "runs")
    app.state.plugin_registry = StaticRegistry(explanation_manifest())
    client = TestClient(app)

    response = client.get(f"/runs/{run_id}/explanations/run")

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["interpretation"]["mode_applied"] == "off"
    assert response.json()["interpretation"]["summary"] is None
