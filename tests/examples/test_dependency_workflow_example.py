from __future__ import annotations

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine


def test_example_dependency_workflow_config_validates() -> None:
    config = load_experiment_config("configs/examples/dependency_workflow.yaml")

    assert config.name == "dependency_workflow_risk_demo"
    assert config.solvers[0].plugin == "dependency_workflow"


def test_example_dependency_workflow_run_completes(tmp_path) -> None:
    config = load_experiment_config("configs/examples/dependency_workflow.yaml")
    config.storage.artifacts_dir = str(tmp_path / "runs")
    config.scheduler.t_end = 5

    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(
        config,
        run_id="dependency-demo",
    )

    assert result.status == "completed"
    assert result.final_time == 5.0
    assert result.metric_summary["delivery_risk_index"] >= 0
