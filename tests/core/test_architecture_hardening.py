from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from persephone_sdk.plugin import Observer, PluginManifest, Renderer, Solver, World

from persephone.config.models import ExperimentConfig, SchedulerConfig, SolverConfig
from persephone.config.schema import core_record_json_schemas
from persephone.core.bus import BusChannelSchema, InMemoryDataBus
from persephone.core.checkpoints import load_checkpoint
from persephone.core.coupling import coupling_registry
from persephone.core.engine import PersephoneEngine
from persephone.core.records import MetricRecord, RecordValidationError
from persephone.core.wrappers import read_declared_bus_channels, write_declared_bus_channels
from persephone.registry.registry import PluginRegistry
from persephone.storage.artifacts import UnsupportedStateValueError
from persephone.storage.sinks import JsonlEventSink, JsonlMetricSink, NpzStateSink
from persephone.sweeps import SweepConfig, execute_sweep


class CadenceWorld(World):
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


class CadenceSolver(Solver):
    def __init__(self) -> None:
        self.rng = np.random.default_rng(0)

    @property
    def preferred_dt(self) -> float:
        return 10.0

    def step(
        self, state: dict[str, np.ndarray], dt: float, bus: Any
    ) -> tuple[dict[str, np.ndarray], float]:
        next_state = {"value": state["value"] + dt}
        bus.write(
            "value",
            next_state["value"],
            solver_id="cadence#0",
            tick=int(next_state["value"][0]),
        )
        return next_state, dt


class CadenceObserver(Observer):
    def observe(self, state: dict[str, np.ndarray], t: float, run_id: str) -> list[dict[str, Any]]:
        return [{"run_id": run_id, "metric": "value", "value": float(state["value"][0]), "t": t}]


class CadenceRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {"type": "line"}


class StaticRegistry(PluginRegistry):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(entry_points_provider=lambda: [])
        self._manifest = manifest

    def discover(self) -> None:
        self._plugins = {"cadence": self._manifest}
        self.load_errors = {}


def cadence_manifest() -> PluginManifest:
    return PluginManifest(
        name="cadence",
        version="0.1.0",
        paradigm="graph",
        world=CadenceWorld,
        solver=CadenceSolver,
        observer=CadenceObserver,
        renderer=CadenceRenderer,
        bus_writes=["value"],
    )


def cadence_config(
    *,
    t_end: float = 1.0,
    sync_interval: float | str = "auto",
    emit_every: float = 1.0,
    checkpoint_every: int | None = None,
) -> ExperimentConfig:
    return ExperimentConfig(
        name="cadence",
        seed=123,
        scheduler=SchedulerConfig(
            t_end=t_end,
            sync_interval=sync_interval,
            checkpoint_every=checkpoint_every,
        ),
        solvers=[SolverConfig(type="graph", plugin="cadence", version=">=0.1.0")],
        observer={"emit_every": emit_every},
    )


def test_metric_record_validation_rejects_bad_records() -> None:
    metric = MetricRecord.model_validate(
        {"run_id": "run-1", "solver_id": "solver#0", "metric": "x", "value": 1, "t": 0}
    )

    assert metric.value == 1.0
    with pytest.raises(RecordValidationError):
        MetricRecord.validate_many([{"run_id": "run-1", "metric": "", "value": "bad", "t": 0}])


def test_scheduler_honors_sync_interval_emit_every_and_writes_telemetry(tmp_path: Path) -> None:
    result = PersephoneEngine(
        registry=StaticRegistry(cadence_manifest()),
        artifact_root=tmp_path / "runs",
    ).run(
        cadence_config(t_end=1.0, sync_interval=0.25, emit_every=0.5),
        run_id="cadence-run",
    )

    assert result.status == "completed"
    metrics = [
        json.loads(line)
        for line in (tmp_path / "runs" / "cadence-run" / "metrics.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    domain_values = [record["value"] for record in metrics if record["metric"] == "value"]
    telemetry = [record for record in metrics if record["metric"] == "scheduler.wall_time_ms"]
    assert domain_values == [0.5, 1.0]
    assert len(telemetry) == 4
    assert telemetry[-1]["tags"]["tick"] == "4"
    assert telemetry[-1]["tags"]["sync_interval_used"] == "0.25"


def test_scheduler_writes_checkpoint_state_bus_rng_and_manifest_metadata(tmp_path: Path) -> None:
    result = PersephoneEngine(
        registry=StaticRegistry(cadence_manifest()),
        artifact_root=tmp_path / "runs",
    ).run(
        cadence_config(t_end=2.0, sync_interval=1.0, emit_every=1.0, checkpoint_every=1),
        run_id="checkpoint-run",
    )

    checkpoint_dir = tmp_path / "runs" / "checkpoint-run" / "checkpoints" / "000001"
    assert result.status == "completed"
    assert (checkpoint_dir / "state.npz").exists()
    assert (checkpoint_dir / "bus.json").exists()
    assert (checkpoint_dir / "rng.json").exists()
    metadata = json.loads((checkpoint_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert metadata["run_id"] == "checkpoint-run"
    assert metadata["tick"] == 1
    assert metadata["schema_version"] == 1

    checkpoint = load_checkpoint(tmp_path / "runs", "checkpoint-run", 1)
    assert checkpoint.metadata["logical_time"] == 1.0
    assert "cadence#0.value" in checkpoint.state
    assert "cadence#0" in checkpoint.rng_states
    np.testing.assert_array_equal(checkpoint.bus.read("value"), np.array([1.0]))


def test_sinks_validate_and_persist_records_in_deterministic_order(tmp_path: Path) -> None:
    metric_sink = JsonlMetricSink(tmp_path / "metrics.jsonl")
    event_sink = JsonlEventSink(tmp_path / "events.jsonl")

    metric_sink.write(
        [
            {"run_id": "run-1", "solver_id": "a", "metric": "x", "value": 2, "t": 2},
            {"run_id": "run-1", "solver_id": "a", "metric": "x", "value": 1, "t": 1},
        ]
    )
    event_sink.write([{"run_id": "run-1", "solver_id": "a", "event": "changed", "t": 1}])

    metric_lines = tmp_path.joinpath("metrics.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["t"] for line in metric_lines] == [1.0, 2.0]
    assert (
        json.loads(tmp_path.joinpath("events.jsonl").read_text(encoding="utf-8"))["event"]
        == "changed"
    )


def test_storage_validation_failures_mark_run_failed_and_emit_telemetry(tmp_path: Path) -> None:
    class InvalidMetricObserver(CadenceObserver):
        def observe(
            self, state: dict[str, np.ndarray], t: float, run_id: str
        ) -> list[dict[str, Any]]:
            return [{"run_id": run_id, "solver_id": "cadence#0", "metric": "", "value": 1, "t": t}]

    manifest = cadence_manifest()
    manifest.observer = InvalidMetricObserver

    result = PersephoneEngine(
        registry=StaticRegistry(manifest),
        artifact_root=tmp_path / "runs",
    ).run(cadence_config(t_end=1.0, sync_interval=1.0), run_id="failed-storage-run")

    assert result.status == "failed"
    assert "metric" in str(result.error_message)
    metrics = [
        json.loads(line)
        for line in (tmp_path / "runs" / "failed-storage-run" / "metrics.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert any(record["metric"] == "scheduler.failure" for record in metrics)


def test_npz_state_sink_rejects_unsupported_state_values(tmp_path: Path) -> None:
    sink = NpzStateSink(tmp_path)

    with pytest.raises(UnsupportedStateValueError, match="MaskedArray"):
        sink.write_state("run-1", {"masked": np.ma.array([1.0], mask=[False])})


def test_bus_snapshot_round_trip_and_commit_summary() -> None:
    bus = InMemoryDataBus(
        run_id="run-1",
        schemas={"x": BusChannelSchema(name="x", dtype="float64", shape=(1,))},
        coupling_rules={"x": "sum"},
    )
    bus.write("x", np.array([1.0]), solver_id="a", tick=1)
    bus.write("x", np.array([2.0]), solver_id="b", tick=1)
    summary = bus.commit(tick=1, logical_time=1.0)
    restored = InMemoryDataBus.from_snapshot(bus.snapshot())

    assert summary.conflicts == {"x": 2}
    np.testing.assert_array_equal(restored.read("x"), np.array([3.0]))


def test_named_coupling_registry_rules_are_resolved_by_bus() -> None:
    coupling_registry.register("max_union", lambda values: np.maximum.reduce(values))
    bus = InMemoryDataBus(
        run_id="run-1",
        schemas={"x": BusChannelSchema(name="x", dtype="int64", shape=(3,))},
        coupling_rules={"x": "max_union"},
    )

    bus.write("x", np.array([0, 1, 0]), solver_id="a", tick=1)
    bus.write("x", np.array([1, 0, 1]), solver_id="b", tick=1)
    bus.commit(tick=1)

    np.testing.assert_array_equal(bus.read("x"), np.array([1, 1, 1]))


def test_declared_bus_helpers_prevent_undeclared_core_coupling() -> None:
    manifest = cadence_manifest()
    bus = InMemoryDataBus(
        run_id="run-1",
        schemas={"value": BusChannelSchema(name="value", dtype="float64", shape=(1,))},
    )

    assert read_declared_bus_channels(manifest, bus) == {}
    write_declared_bus_channels(
        manifest,
        {"value": np.array([1.0], dtype=np.float64)},
        bus,
        solver_id="cadence#0",
        tick=1,
        logical_time=1.0,
    )

    with pytest.raises(ValueError, match="undeclared"):
        write_declared_bus_channels(
            manifest,
            {"aerosol_grid": np.array([1.0])},
            bus,
            solver_id="cadence#0",
            tick=1,
        )


def test_same_seed_reproducibility_through_public_engine_api(tmp_path: Path) -> None:
    engine = PersephoneEngine(
        registry=StaticRegistry(cadence_manifest()),
        artifact_root=tmp_path / "runs",
    )

    first = engine.run(cadence_config(t_end=2.0, sync_interval=1.0), run_id="same-seed-a")
    second = engine.run(cadence_config(t_end=2.0, sync_interval=1.0), run_id="same-seed-b")

    assert first.status == "completed"
    assert second.status == "completed"
    first_metrics = [
        (record["t"], record["metric"], record["value"])
        for record in (
            json.loads(line)
            for line in (tmp_path / "runs" / "same-seed-a" / "metrics.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        if record["metric"] == "value"
    ]
    second_metrics = [
        (record["t"], record["metric"], record["value"])
        for record in (
            json.loads(line)
            for line in (tmp_path / "runs" / "same-seed-b" / "metrics.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        if record["metric"] == "value"
    ]
    assert first_metrics == second_metrics


def test_sweep_reproducibility_preserves_child_trajectories(tmp_path: Path) -> None:
    base_config = cadence_config(t_end=2.0, sync_interval=1.0)
    first = execute_sweep(
        SweepConfig(
            sweep_id="sweep-a",
            name="A",
            base_config=base_config,
            parameter="scheduler.t_end",
            values=[2.0],
        ),
        artifact_root=tmp_path / "runs",
        engine_factory=lambda root: PersephoneEngine(
            registry=StaticRegistry(cadence_manifest()),
            artifact_root=root,
        ),
    )
    second = execute_sweep(
        SweepConfig(
            sweep_id="sweep-b",
            name="B",
            base_config=base_config,
            parameter="scheduler.t_end",
            values=[2.0],
        ),
        artifact_root=tmp_path / "runs",
        engine_factory=lambda root: PersephoneEngine(
            registry=StaticRegistry(cadence_manifest()),
            artifact_root=root,
        ),
    )

    def domain_values(run_id: str) -> list[float]:
        return [
            record["value"]
            for record in (
                json.loads(line)
                for line in (tmp_path / "runs" / run_id / "metrics.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            )
            if record["metric"] == "value"
        ]

    assert domain_values(first.child_runs[0].run_id) == domain_values(second.child_runs[0].run_id)


def test_core_record_json_schema_export_includes_metrics_and_telemetry() -> None:
    schemas = core_record_json_schemas()

    assert "MetricRecord" in schemas
    assert "SchedulerTelemetry" in schemas
    assert schemas["MetricRecord"]["properties"]["metric"]["type"] == "string"
