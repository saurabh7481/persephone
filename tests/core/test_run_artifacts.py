from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from persephone_sdk.plugin import Observer, PluginManifest, Renderer, Solver, World

from persephone.config.load import load_experiment_config
from persephone.core.run import RunContext
from persephone.storage.artifacts import ArtifactStore


class ArtifactWorld(World):
    def schema(self) -> dict[str, tuple[int, ...]]:
        return {"x": (1,)}

    def init(self, params: dict[str, Any], seed: int) -> dict[str, np.ndarray]:
        return {"x": np.array([0.0])}

    def reset(self) -> dict[str, np.ndarray]:
        return {"x": np.array([0.0])}


class ArtifactSolver(Solver):
    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(
        self, state: dict[str, np.ndarray], dt: float, bus: Any
    ) -> tuple[dict[str, np.ndarray], float]:
        return state, dt


class ArtifactObserver(Observer):
    def observe(self, state: dict[str, np.ndarray], t: float, run_id: str) -> list[dict[str, Any]]:
        return []


class ArtifactRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {"type": "none"}


def write_config(tmp_path: Path) -> Path:
    data_path = tmp_path / "edges.csv"
    data_path.write_text("source,target,weight\n0,1,1.0\n", encoding="utf-8")
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        """
name: sir_smoke
seed: 42
scheduler:
  t_end: 10
solvers:
  - type: graph
    plugin: sir_epidemic
    version: ">=0.1.0"
    params:
      contact_graph: edges.csv
      p_infect: 0.1
  - type: graph
    plugin: graph_probe
    version: ">=0.1.0"
    params: {}
""",
        encoding="utf-8",
    )
    return config_path


def plugin_manifest(name: str, version: str) -> PluginManifest:
    return PluginManifest(
        name=name,
        version=version,
        paradigm="graph",
        world=ArtifactWorld,
        solver=ArtifactSolver,
        observer=ArtifactObserver,
        renderer=ArtifactRenderer,
        bus_reads=[],
        bus_writes=[],
        default_params={},
        params_schema={},
        metrics_schema={},
        sdk_min_version="0.1.0",
    )


def test_run_context_records_manifest_provenance_and_reproducible_seed_plan(tmp_path: Path) -> None:
    config = load_experiment_config(write_config(tmp_path))
    manifests = {
        "sir_epidemic": plugin_manifest("sir_epidemic", "0.1.0"),
        "graph_probe": plugin_manifest("graph_probe", "0.2.0"),
    }

    first = RunContext.create(config=config, plugin_manifests=manifests)
    second = RunContext.create(config=config, plugin_manifests=manifests)

    assert first.config_hash == second.config_hash
    assert first.seed_plan == second.seed_plan
    assert first.plugin_versions == {"sir_epidemic": "0.1.0", "graph_probe": "0.2.0"}
    assert set(first.seed_plan) == {"sir_epidemic#0", "graph_probe#1"}


def test_artifact_store_writes_manifest_metrics_events_and_final_state(tmp_path: Path) -> None:
    config = load_experiment_config(write_config(tmp_path))
    manifests = {
        "sir_epidemic": plugin_manifest("sir_epidemic", "0.1.0"),
        "graph_probe": plugin_manifest("graph_probe", "0.2.0"),
    }
    context = RunContext.create(config=config, plugin_manifests=manifests, run_id="run-test")
    store = ArtifactStore(root=tmp_path / "runs")

    run_dir = store.initialize_run(context)
    store.write_metrics(context.run_id, [{"metric": "infected_count", "value": 3, "t": 1.0}])
    store.write_events(context.run_id, [{"event": "infection", "entity_id": 1, "t": 1.0}])
    store.write_final_state(context.run_id, {"state": np.array([0, 1, 2])})
    store.update_status(context.run_id, "completed", t_current=10.0)

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = (run_dir / "metrics.jsonl").read_text(encoding="utf-8").strip().splitlines()
    events = (run_dir / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    state = np.load(run_dir / "final_state.npz")

    assert manifest["run_id"] == "run-test"
    assert manifest["status"] == "completed"
    assert manifest["t_current"] == 10.0
    assert json.loads(metrics[0])["metric"] == "infected_count"
    assert json.loads(events[0])["event"] == "infection"
    np.testing.assert_array_equal(state["state"], np.array([0, 1, 2]))
    assert (run_dir / "final_state.json").exists()
