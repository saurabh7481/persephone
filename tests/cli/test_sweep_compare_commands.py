from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from persephone.cli.main import app
from persephone.config.load import load_experiment_config


def test_sweep_command_executes_yaml_sweep(tmp_path: Path) -> None:
    base_config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    sweep_path = tmp_path / "sweep.yaml"
    sweep_path.write_text(
        yaml.safe_dump(
            {
                "sweep_id": "cli-sweep",
                "name": "CLI sweep",
                "base_config": base_config.model_dump(mode="json"),
                "parameter": "solvers[0].params.p_infect",
                "values": [0.2, 0.4],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["sweep", str(sweep_path), "--artifacts-dir", str(tmp_path / "runs")],
    )

    assert result.exit_code == 0
    assert "cli-sweep" in result.output
    assert (tmp_path / "runs" / "cli-sweep" / "sweep.json").exists()


def test_compare_command_prints_metric_summary(tmp_path: Path) -> None:
    runner = CliRunner()
    for run_id in ["compare-a", "compare-b"]:
        run_result = runner.invoke(
            app,
            [
                "run",
                "configs/examples/sir_epidemic.yaml",
                "--run-id",
                run_id,
                "--artifacts-dir",
                str(tmp_path / "runs"),
            ],
        )
        assert run_result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "compare",
            "compare-a",
            "compare-b",
            "--metric",
            "infected_count",
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code == 0
    assert "infected_count" in result.output
    assert "peak" in result.output
