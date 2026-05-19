from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from persephone.cli.main import app


def test_run_command_creates_artifacts(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "run",
            "configs/examples/sir_epidemic.yaml",
            "--run-id",
            "cli-run",
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code == 0
    assert "completed" in result.output
    assert (tmp_path / "runs" / "cli-run" / "manifest.json").exists()


def test_runs_show_metrics_and_replay_commands_read_artifacts(tmp_path: Path) -> None:
    runner = CliRunner()
    run_result = runner.invoke(
        app,
        [
            "run",
            "configs/examples/sir_epidemic.yaml",
            "--run-id",
            "cli-run",
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )
    assert run_result.exit_code == 0
    run_path = tmp_path / "runs" / "cli-run"

    show_result = runner.invoke(
        app, ["runs", "show", "cli-run", "--artifacts-dir", str(tmp_path / "runs")]
    )
    metrics_result = runner.invoke(
        app,
        [
            "runs",
            "metrics",
            "cli-run",
            "--metric",
            "infected_count",
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )
    replay_result = runner.invoke(app, ["replay", str(run_path)])

    assert show_result.exit_code == 0
    assert "cli-run" in show_result.output
    assert metrics_result.exit_code == 0
    assert "infected_count" in metrics_result.output
    assert replay_result.exit_code == 0
    assert "infected_count" in replay_result.output

    manifest = json.loads((run_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
