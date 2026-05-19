from __future__ import annotations

from pathlib import Path

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine


def test_example_sir_config_validates() -> None:
    config = load_experiment_config("configs/examples/sir_epidemic.yaml")

    assert config.name == "sir_epidemic_baseline"
    assert Path(config.solvers[0].params["contact_graph"]).exists()


def test_example_sir_run_completes(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    config.storage.artifacts_dir = str(tmp_path / "runs")
    config.scheduler.t_end = 6

    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(config, run_id="sir-example")

    assert result.status == "completed"
    assert result.final_time == 6.0
    assert (result.artifact_path / "metrics.jsonl").exists()
    assert result.metric_summary["infected_count"] >= 0
