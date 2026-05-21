from __future__ import annotations

from pathlib import Path

from persephone_sdk.testing import PluginTestHarness
from typer.testing import CliRunner

from persephone.cli.main import app


def test_export_command_writes_csv_and_parquet(tmp_path: Path) -> None:
    runner = CliRunner()
    run = runner.invoke(
        app,
        [
            "run",
            "configs/examples/sir_epidemic.yaml",
            "--run-id",
            "cli-export",
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )
    assert run.exit_code == 0

    csv_result = runner.invoke(
        app,
        [
            "export",
            "cli-export",
            "--format",
            "csv",
            "--output",
            str(tmp_path / "csv"),
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )
    parquet_result = runner.invoke(
        app,
        [
            "export",
            "cli-export",
            "--format",
            "parquet",
            "--output",
            str(tmp_path / "parquet"),
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )

    assert csv_result.exit_code == 0
    assert parquet_result.exit_code == 0
    assert (tmp_path / "csv" / "metrics.csv").exists()
    assert (tmp_path / "parquet" / "metrics.parquet").exists()


def test_fields_list_and_export_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    run = runner.invoke(
        app,
        [
            "run",
            "configs/examples/heat_diffusion.yaml",
            "--run-id",
            "cli-field",
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )
    assert run.exit_code == 0

    listed = runner.invoke(
        app, ["fields", "list", "cli-field", "--artifacts-dir", str(tmp_path / "runs")]
    )
    exported = runner.invoke(
        app,
        [
            "fields",
            "export",
            "cli-field",
            "final_state:heat_diffusion#0.temperature",
            "--output",
            str(tmp_path / "temperature.csv"),
            "--artifacts-dir",
            str(tmp_path / "runs"),
        ],
    )

    assert listed.exit_code == 0
    assert "temperature" in listed.output
    assert exported.exit_code == 0
    assert (tmp_path / "temperature.csv").exists()


def test_plugins_scaffold_generates_importable_plugin_layout(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["plugins", "scaffold", "demo-model", "--output-dir", str(tmp_path)],
    )

    plugin_root = tmp_path / "persephone-plugin-demo-model"
    package_root = plugin_root / "src" / "persephone_demo_model"

    assert result.exit_code == 0
    assert (plugin_root / "pyproject.toml").exists()
    assert (package_root / "__init__.py").exists()
    assert (package_root / "world.py").exists()
    assert (package_root / "solver.py").exists()
    assert (package_root / "observer.py").exists()
    assert (package_root / "renderer.py").exists()
    assert (plugin_root / "tests" / "test_demo_model_plugin.py").exists()

    import sys

    sys.path.insert(0, str(plugin_root / "src"))
    try:
        from persephone_demo_model import DemoModelPlugin

        PluginTestHarness(DemoModelPlugin).run_all()
    finally:
        sys.path.remove(str(plugin_root / "src"))
