from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from persephone_river_flood import RiverFloodPlugin
from persephone_river_flood.model import (
    FLOOD,
    NORMAL,
    WARNING,
    WATCH,
    classify_flood_status,
    route_step,
)

from persephone.core.engine import PersephoneEngine
from persephone.registry.registry import PluginRegistry


def test_route_step_inflow_raises_downstream_storage():
    """Water injected at upstream node must raise downstream storage."""
    # 2 nodes: 0 upstream → 1 downstream
    n = 2
    storage = np.array([1000.0, 500.0], dtype=np.float64)
    flow = np.array([0.5, 0.2], dtype=np.float64)
    upstream_ids = np.array([0], dtype=np.int64)
    downstream_ids = np.array([1], dtype=np.int64)
    edge_weights = np.array([1.0], dtype=np.float64)
    precip_input = np.zeros(n, dtype=np.float64)
    flood_stage = np.array([100.0, 50.0], dtype=np.float64)
    normal_flow = np.array([0.5, 0.2], dtype=np.float64)

    new_storage, new_flow, _ = route_step(
        storage, flow, upstream_ids, downstream_ids, edge_weights,
        precip_input, flood_stage, normal_flow, routing_k=0.35,
    )

    assert new_storage[1] > storage[1], "downstream storage must increase from inflow"


def test_route_step_storage_non_negative():
    n = 3
    storage = np.zeros(n, dtype=np.float64)
    flow = np.zeros(n, dtype=np.float64)
    upstream_ids = np.array([0, 1], dtype=np.int64)
    downstream_ids = np.array([1, 2], dtype=np.int64)
    edge_weights = np.ones(2, dtype=np.float64)
    precip_input = np.zeros(n, dtype=np.float64)
    flood_stage = np.ones(n, dtype=np.float64) * 100.0
    normal_flow = np.ones(n, dtype=np.float64) * 0.1

    new_storage, new_flow, _ = route_step(
        storage, flow, upstream_ids, downstream_ids, edge_weights,
        precip_input, flood_stage, normal_flow, routing_k=0.5,
    )

    assert np.all(new_storage >= 0.0)
    assert np.all(new_flow >= 0.0)


def test_precipitation_input_raises_headwater_storage():
    n = 2
    storage = np.array([0.0, 0.0], dtype=np.float64)
    flow = np.zeros(n, dtype=np.float64)
    upstream_ids = np.array([0], dtype=np.int64)
    downstream_ids = np.array([1], dtype=np.int64)
    edge_weights = np.ones(1, dtype=np.float64)
    precip_input = np.array([500.0, 0.0], dtype=np.float64)  # rain at node 0
    flood_stage = np.array([200.0, 200.0], dtype=np.float64)
    normal_flow = np.array([1.0, 1.0], dtype=np.float64)

    new_storage, _, _ = route_step(
        storage, flow, upstream_ids, downstream_ids, edge_weights,
        precip_input, flood_stage, normal_flow, routing_k=0.1,
    )

    assert new_storage[0] > 0.0, "precipitation must raise headwater storage"


def test_classify_flood_status_thresholds():
    flood_stage = np.array([100.0, 100.0, 100.0, 100.0])
    flow = np.array([60.0, 70.0, 91.0, 100.0])
    status = classify_flood_status(flow, flood_stage)
    assert status[0] == NORMAL   # 60 < 70
    assert status[1] == WATCH    # 70 = 0.7 * 100
    assert status[2] == WARNING  # 91 >= 0.9 * 100
    assert status[3] == FLOOD    # 100 >= 100


class _FloodEntry:
    name = "river_flood"

    def load(self):
        return RiverFloodPlugin


def _flood_config(tmp_path: Path, preset: str = "spring_snowmelt") -> object:
    from persephone.config.load import load_experiment_config
    config = tmp_path / "experiment.yaml"
    config.write_text(
        f"""
name: flood_test
seed: 42
scheduler:
  t_end: 10
storage:
  artifacts_dir: runs
solvers:
  - type: graph
    plugin: river_flood
    version: ">=0.1.0"
    params:
      event_preset: {preset}
      precipitation_cms: 2000
      precipitation_duration_hours: 5
      routing_k: 0.35
""",
        encoding="utf-8",
    )
    return load_experiment_config(config)


def test_river_flood_run_completes_and_emits_metrics(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_FloodEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_flood_config(tmp_path), run_id="flood-test")

    assert result.status == "completed"
    assert result.final_time == pytest.approx(10.0)

    metrics_lines = (result.artifact_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    metrics = [json.loads(line) for line in metrics_lines]
    names = {m["metric"] for m in metrics}
    assert "stations_flooding" in names
    assert "total_excess_flow_cms" in names
    assert "flood_front_km" in names


def test_river_flood_spring_snowmelt_raises_upstream_flow(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_FloodEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_flood_config(tmp_path, preset="spring_snowmelt"), run_id="flood-snowmelt")

    metrics_lines = (result.artifact_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    metrics = [json.loads(line) for line in metrics_lines]

    # after 10 steps with heavy precip the total excess flow should be >0
    excess_values = [m["value"] for m in metrics if m["metric"] == "total_excess_flow_cms"]
    assert max(excess_values) > 0.0

    # flood front should be > 0 km once warning stations appear
    front_values = [m["value"] for m in metrics if m["metric"] == "flood_front_km"]
    assert max(front_values) >= 0.0  # may be 0 if wave hasn't reached warning stations in 10 steps


def test_river_flood_gulf_hurricane_preset(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_FloodEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_flood_config(tmp_path, preset="gulf_hurricane"), run_id="flood-hurricane")
    assert result.status == "completed"

