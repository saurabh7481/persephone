from __future__ import annotations

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine


def test_example_market_stress_config_validates() -> None:
    config = load_experiment_config("configs/examples/market_stress.yaml")

    assert config.name == "market_stress_rotation_demo"
    assert config.solvers[0].plugin == "market_stress"


def test_example_market_stress_run_completes(tmp_path) -> None:
    config = load_experiment_config("configs/examples/market_stress.yaml")
    config.storage.artifacts_dir = str(tmp_path / "runs")
    config.scheduler.t_end = 5

    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(config, run_id="market-demo")

    assert result.status == "completed"
    assert result.final_time == 5.0
    assert result.metric_summary["portfolio_stress_index"] >= 0
