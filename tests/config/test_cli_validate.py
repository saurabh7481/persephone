from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from persephone.cli.main import app

runner = CliRunner()


def test_validate_command_accepts_valid_config(tmp_path: Path) -> None:
    (tmp_path / "edges.csv").write_text("source,target,weight\n0,1,1.0\n", encoding="utf-8")
    config = tmp_path / "experiment.yaml"
    config.write_text(
        """
name: sir_smoke
seed: 42
scheduler:
  t_end: 10
solvers:
  - type: graph
    plugin: sir_epidemic
    version: ">=0.1.0"
    params:
      contact_graph: edges.csv
      p_infect: 0.1
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate", str(config)])

    assert result.exit_code == 0
    assert "valid" in result.output.lower()


def test_validate_command_reports_invalid_config(tmp_path: Path) -> None:
    config = tmp_path / "experiment.yaml"
    config.write_text(
        """
name: missing_data
seed: 42
scheduler:
  t_end: 10
solvers:
  - type: graph
    plugin: sir_epidemic
    version: ">=0.1.0"
    params:
      contact_graph: missing.csv
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate", str(config)])

    assert result.exit_code == 1
    assert "missing.csv" in result.output
