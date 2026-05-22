from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from persephone_sdk.plugin import Observer, PluginManifest, Renderer, Solver, World

from persephone.config.models import ExperimentConfig, SchedulerConfig, SolverConfig
from persephone.config.schema import core_record_json_schemas
from persephone.core.engine import PersephoneEngine
from persephone.core.explanations import (
    ExplanationPacket,
    MilestoneFact,
    TrendFact,
    summarize_explanation_packet,
)
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
    )


def explanation_config() -> ExperimentConfig:
    return ExperimentConfig(
        name="explain",
        seed=7,
        scheduler=SchedulerConfig(t_end=1.0, sync_interval=1.0),
        solvers=[SolverConfig(type="graph", plugin="explain", version=">=0.1.0")],
        observer={"emit_every": 1.0},
        visualization={"emit_every": 1.0},
    )


def test_rules_only_summarizer_prioritizes_highest_severity_fact() -> None:
    packet = ExplanationPacket(
        run_id="run-a",
        solver_id="solver#0",
        scope="run",
        t=3.0,
        tick=3,
        facts=[
            TrendFact(
                title="Infections rising",
                summary="Infected count increased over the last interval.",
                severity="warning",
                evidence=[{"label": "infected_count", "value": 12}],
                related_ids=["infected_count"],
                t=3.0,
            ),
            MilestoneFact(
                title="Recovery threshold reached",
                summary="Recovered count passed the configured milestone.",
                severity="info",
                evidence=[{"label": "recovered_count", "value": 5}],
                related_ids=["recovered_count"],
                t=3.0,
            ),
        ],
    )

    summary = summarize_explanation_packet(packet)

    assert summary.severity == "warning"
    assert summary.fact_count == 2
    assert "2 findings" in summary.summary
    assert summary.evidence[0].label == "infected_count"


def test_engine_persists_explanation_packets_with_rules_only_summaries(tmp_path: Path) -> None:
    result = PersephoneEngine(
        registry=StaticRegistry(explanation_manifest()),
        artifact_root=tmp_path / "runs",
    ).run(explanation_config(), run_id="explain-run")

    explanation_path = tmp_path / "runs" / "explain-run" / "explanations" / "facts.jsonl"
    packets = [
        json.loads(line)
        for line in explanation_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert result.status == "completed"
    assert [packet["scope"] for packet in packets] == ["frame", "run", "selection"]
    assert packets[0]["summary"]["fact_count"] == 1
    assert packets[1]["facts"][0]["kind"] == "trend"
    assert packets[2]["selection_id"] == "population"


def test_core_record_schema_export_contains_explanation_models() -> None:
    schemas = core_record_json_schemas()

    assert "ExplanationPacket" in schemas
    assert "ExplanationSummary" in schemas
    assert "TrendFact" in schemas
