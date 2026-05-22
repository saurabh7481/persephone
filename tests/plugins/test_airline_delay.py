from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from persephone_airline_delay import AirlineDelayPlugin
from persephone_airline_delay.model import (
    DISRUPTED,
    MAJOR,
    MINOR,
    NORMAL,
    classify_status,
    delay_step,
)

from persephone.core.engine import PersephoneEngine
from persephone.registry.registry import PluginRegistry


def _simple_graph():
    """Triangle: 0-1-2-0 with equal weights."""
    sources = np.array([0, 1, 2], dtype=np.int64)
    targets = np.array([1, 2, 0], dtype=np.int64)
    weights = np.ones(3, dtype=np.float64)
    return sources, targets, weights


def test_delay_step_propagates_from_delayed_airport():
    sources, targets, weights = _simple_graph()
    delay = np.array([120.0, 0.0, 0.0], dtype=np.float64)
    result = delay_step(delay, sources, targets, weights, propagation_factor=0.3, recovery_rate=0.0)
    # airport 0 pushes to airport 1 (edge 0→1), airport 2 pushes 0 via edge 2→0
    # airport 0 has delay; targets of edges FROM 0 = node 1 via edge[0]; also node 0 receives from node 2 (edge[2])
    assert result[1] > 0.0, "delay must propagate to neighbour"
    assert result[0] == pytest.approx(120.0, rel=0.01), "no recovery when rate=0"


def test_delay_step_recovery_drains_delay():
    sources, targets, weights = _simple_graph()
    delay = np.array([100.0, 0.0, 0.0], dtype=np.float64)
    result = delay_step(delay, sources, targets, weights, propagation_factor=0.0, recovery_rate=0.2)
    assert result[0] == pytest.approx(80.0), "20% recovery applied"
    assert result[1] == 0.0
    assert result[2] == 0.0


def test_delay_step_never_goes_negative():
    sources, targets, weights = _simple_graph()
    delay = np.array([0.0, 0.0, 0.0], dtype=np.float64)
    result = delay_step(delay, sources, targets, weights, propagation_factor=0.5, recovery_rate=0.99)
    assert np.all(result >= 0.0)


def test_classify_status_thresholds():
    delay = np.array([0.0, 14.9, 15.0, 44.9, 45.0, 119.9, 120.0, 200.0])
    status = classify_status(delay)
    assert status[0] == NORMAL
    assert status[1] == NORMAL
    assert status[2] == MINOR
    assert status[3] == MINOR
    assert status[4] == MAJOR
    assert status[5] == MAJOR
    assert status[6] == DISRUPTED
    assert status[7] == DISRUPTED


class _AirlineEntry:
    name = "airline_delay"

    def load(self):
        return AirlineDelayPlugin


def _write_config(tmp_path: Path, initial_airports: list[str] | None = None) -> Path:
    airports = initial_airports or ["JFK", "LHR"]
    airports_yaml = "[" + ", ".join(f'"{a}"' for a in airports) + "]"
    config = tmp_path / "experiment.yaml"
    config.write_text(
        f"""
name: airline_test
seed: 42
scheduler:
  t_end: 5
storage:
  artifacts_dir: runs
solvers:
  - type: graph
    plugin: airline_delay
    version: ">=0.1.0"
    params:
      initial_airports: {airports_yaml}
      initial_delay_minutes: 180
      propagation_factor: 0.3
      recovery_rate: 0.1
""",
        encoding="utf-8",
    )
    return config


def test_airline_delay_run_completes_and_emits_metrics(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_AirlineEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_write_config_obj(tmp_path), run_id="airline-test")

    assert result.status == "completed"
    assert result.final_time == pytest.approx(5.0)

    metrics_lines = (result.artifact_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    metrics = [json.loads(line) for line in metrics_lines]
    names = {m["metric"] for m in metrics}
    assert "disrupted_airports" in names
    assert "total_delay_minutes" in names
    assert "cascade_reach" in names

    # initial shock of 180 min per airport means cascade_reach > 0 after step 1
    final_reach = max(m["value"] for m in metrics if m["metric"] == "cascade_reach")
    assert final_reach >= 2  # at least the 2 seeded airports were delayed


def _write_config_obj(tmp_path: Path):
    from persephone.config.load import load_experiment_config
    return load_experiment_config(_write_config(tmp_path))


def test_airline_delay_delay_propagates_beyond_seed_airports(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_AirlineEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_write_config_obj(tmp_path), run_id="airline-cascade")

    metrics_lines = (result.artifact_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    metrics = [json.loads(line) for line in metrics_lines]

    # after 5 steps with prop_factor=0.3, at least some neighbours must be delayed
    delayed_at_end = [m["value"] for m in metrics if m["metric"] == "delayed_airports"]
    assert max(delayed_at_end) > 2

