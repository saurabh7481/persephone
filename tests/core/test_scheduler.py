from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from persephone_sdk.plugin import Observer, PluginManifest, Renderer, Solver, World

from persephone.config.models import ExperimentConfig, SchedulerConfig, SolverConfig
from persephone.core.bus import BusChannelSchema, InMemoryDataBus
from persephone.core.run import RunContext
from persephone.core.scheduler import Scheduler, SolverRuntime
from persephone.storage.artifacts import ArtifactStore


class FakeWorld(World):
    def __init__(self) -> None:
        self._initial: dict[str, np.ndarray] | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        return {"value": (1,)}

    def init(self, params: dict[str, Any], seed: int) -> dict[str, np.ndarray]:
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
        self, state: dict[str, np.ndarray], dt: float, bus: Any
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
    def observe(self, state: dict[str, np.ndarray], t: float, run_id: str) -> list[dict[str, Any]]:
        return [
            {
                "run_id": run_id,
                "metric": "fake_value",
                "value": float(state["value"][0]),
                "t": t,
            }
        ]


class FakeRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {"type": "line"}


def config(t_end: float = 3.0) -> ExperimentConfig:
    return ExperimentConfig(
        name="scheduler_test",
        seed=7,
        scheduler=SchedulerConfig(t_end=t_end),
        solvers=[SolverConfig(type="graph", plugin="fake", version=">=0.1.0")],
    )


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


def runtime(solver: Any | None = None) -> SolverRuntime:
    state = {"value": np.array([0.0], dtype=np.float64)}
    return SolverRuntime(
        solver_id="fake#0",
        solver=solver or FakeSolver(),
        observer=FakeObserver(),
        renderer=FakeRenderer(),
        state=state,
        rng=np.random.default_rng(123),
    )


def make_scheduler(tmp_path: Path, solver: Any | None = None, t_end: float = 3.0) -> Scheduler:
    run_context = RunContext.create(
        config(t_end=t_end),
        {"fake": manifest()},
        run_id="run-scheduler",
    )
    store = ArtifactStore(tmp_path / "runs")
    store.initialize_run(run_context)
    bus = InMemoryDataBus(
        run_id=run_context.run_id,
        schemas={"value": BusChannelSchema(name="value", dtype="float64", shape=(1,))},
    )
    return Scheduler(
        run_context=run_context,
        runtimes=[runtime(solver)],
        bus=bus,
        artifact_store=store,
    )


def test_scheduler_advances_exact_tick_count_and_emits_metrics(tmp_path: Path) -> None:
    scheduler = make_scheduler(tmp_path, t_end=3.0)

    result = scheduler.run()

    assert result.status == "completed"
    assert result.tick_count == 3
    assert result.t_current == 3.0
    metric_lines = [
        json.loads(line)
        for line in (tmp_path / "runs" / "run-scheduler" / "metrics.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    ]
    domain_metrics = [record for record in metric_lines if record["metric"] == "fake_value"]
    assert len(domain_metrics) == 3
    assert domain_metrics[-1]["value"] == 3.0


def test_scheduler_records_failed_manifest_without_swallowing_error(tmp_path: Path) -> None:
    class FailingSolver(FakeSolver):
        def step(self, state: dict[str, np.ndarray], dt: float, bus: Any):
            raise RuntimeError("solver exploded")

    scheduler = make_scheduler(tmp_path, solver=FailingSolver())

    result = scheduler.run()

    manifest_data = json.loads(
        (tmp_path / "runs" / "run-scheduler" / "manifest.json").read_text(encoding="utf-8")
    )
    assert result.status == "failed"
    assert result.error_message == "solver exploded"
    assert manifest_data["status"] == "failed"
    assert manifest_data["error_message"] == "solver exploded"


def test_scheduler_rejects_non_positive_solver_elapsed_time(tmp_path: Path) -> None:
    class StalledSolver(FakeSolver):
        def step(self, state: dict[str, np.ndarray], dt: float, bus: Any):
            return state, 0.0

    scheduler = make_scheduler(tmp_path, solver=StalledSolver())

    result = scheduler.run()

    assert result.status == "failed"
    assert "positive elapsed time" in str(result.error_message)
