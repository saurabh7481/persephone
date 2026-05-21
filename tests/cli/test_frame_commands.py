from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from persephone.cli.main import app


def test_frame_commands_list_show_and_export(tmp_path: Path) -> None:
    runner = CliRunner()
    run_result = runner.invoke(
        app,
        [
            "run",
            "configs/examples/heat_diffusion.yaml",
            "--run-id",
            "frame-cli",
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )
    assert run_result.exit_code == 0

    list_result = runner.invoke(
        app,
        ["frames", "list", "frame-cli", "--artifacts-dir", str(tmp_path / "runs")],
    )
    assert list_result.exit_code == 0
    assert "field" in list_result.output
    frame_id = "heat_diffusion#0:temperature:000011"

    show_result = runner.invoke(
        app,
        ["frames", "show", "frame-cli", frame_id, "--artifacts-dir", str(tmp_path / "runs")],
    )
    assert show_result.exit_code == 0
    assert "temperature" in show_result.output

    output = tmp_path / "frame.json"
    export_result = runner.invoke(
        app,
        [
            "frames",
            "export",
            "frame-cli",
            frame_id,
            "--output",
            str(output),
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )
    assert export_result.exit_code == 0
    assert output.exists()
    assert "temperature" in output.read_text(encoding="utf-8")
