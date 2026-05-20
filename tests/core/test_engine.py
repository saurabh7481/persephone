from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from persephone_sdk.plugin import Observer, PluginManifest, Renderer, Solver, World

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine
from persephone.registry.registry import PluginRegistry


class FakeWorld(World):
    def __init__(self) -> None:
        self._initial: dict[str, np.ndarray] | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        return {"value": (1,)}

    def init(self, params: dict[str, object], seed: int) -> dict[str, np.ndarray]:
        self._initial = {"value": np.array([0.0], dtype=np.float64)}
        return {"value": self._initial["value"].copy()}

    def reset(self) -> dict[str, np.ndarray]:
        assert self._initial is not None
        return {"value": self._initial["value"].copy()}


class FakeSolver(Solver):
    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(
        self, state: dict[str, np.ndarray], dt: float, bus: object
    ) -> tuple[dict[str, np.ndarray], float]:
        next_state = {"value": state["value"] + dt}
        bus.write(
            "value",
            next_state["value"],
            solver_id="fake#0",
            tick=int(next_state["value"][0]),
        )
        return next_state, dt


class FakeObserver(Observer):
    def observe(
        self, state: dict[str, np.ndarray], t: float, run_id: str
    ) -> list[dict[str, object]]:
        return [
            {
                "run_id": run_id,
                "metric": "fake_value",
                "value": float(state["value"][0]),
                "t": t,
            }
        ]


class FakeRenderer(Renderer):
    def viz_schema(self) -> dict[str, object]:
        return {"type": "line"}


class FakePlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="fake",
            version="0.1.0",
            paradigm="graph",
            world=FakeWorld,
            solver=FakeSolver,
            observer=FakeObserver,
            renderer=FakeRenderer,
            bus_reads=[],
            bus_writes=["value"],
            default_params={},
            params_schema={},
            metrics_schema={},
            sdk_min_version="0.1.0",
        )


class FakeEntryPoint:
    name = "fake"

    def load(self):
        return FakePlugin


def write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        """
name: engine_test
seed: 11
scheduler:
  t_end: 2
storage:
  artifacts_dir: runs
solvers:
  - type: graph
    plugin: fake
    version: ">=0.1.0"
    params: {}
""",
        encoding="utf-8",
    )
    return config_path


def test_engine_validate_resolves_required_plugins(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [FakeEntryPoint()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    config = load_experiment_config(write_config(tmp_path))

    manifests = engine.validate(config)

    assert manifests["fake"].version == "0.1.0"


def test_engine_run_wires_runtime_and_writes_artifacts(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [FakeEntryPoint()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")

    result = engine.run(load_experiment_config(write_config(tmp_path)), run_id="run-engine")

    assert result.status == "completed"
    assert result.final_time == 2.0
    assert result.metric_summary["fake_value"] == 2.0
    assert result.artifact_path == tmp_path / "runs" / "run-engine"
    manifest = json.loads((result.artifact_path / "manifest.json").read_text(encoding="utf-8"))
    metrics = [
        json.loads(line)
        for line in (result.artifact_path / "metrics.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    domain_metrics = [record for record in metrics if record["metric"] == "fake_value"]
    state = np.load(result.artifact_path / "final_state.npz")
    assert manifest["status"] == "completed"
    assert len(domain_metrics) == 2
    np.testing.assert_array_equal(state["fake#0.value"], np.array([2.0]))
