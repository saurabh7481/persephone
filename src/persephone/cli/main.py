from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, cast

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from persephone.compare import compare_metric_records
from persephone.config.load import load_experiment_config
from persephone.core.checkpoints import load_checkpoint
from persephone.core.engine import PersephoneEngine
from persephone.export import export_run
from persephone.fields import export_field_artifact, list_field_artifacts
from persephone.frames import (
    FrameNotFoundError,
    UnsupportedFrameFormatError,
    export_frame,
    get_frame,
    list_frames,
)
from persephone.registry.registry import PluginRegistry
from persephone.scaffold import scaffold_plugin
from persephone.storage.catalog import RunCatalog, RunCatalogError
from persephone.sweeps import SweepConfig, execute_sweep

app = typer.Typer(help="Persephone simulation platform CLI.")
plugins_app = typer.Typer(help="Inspect installed simulation plugins.")
runs_app = typer.Typer(help="Inspect completed simulation runs.")
examples_app = typer.Typer(help="Generate example inputs.")
checkpoints_app = typer.Typer(help="Inspect simulation checkpoints.")
fields_app = typer.Typer(help="Inspect and export field artifacts.")
frames_app = typer.Typer(help="Inspect and export simulation frames.")
app.add_typer(plugins_app, name="plugins")
app.add_typer(runs_app, name="runs")
app.add_typer(examples_app, name="examples")
app.add_typer(checkpoints_app, name="checkpoints")
app.add_typer(fields_app, name="fields")
app.add_typer(frames_app, name="frames")
console = Console()


@app.callback()
def main() -> None:
    """Run and inspect Persephone simulations."""


@app.command()
def validate(
    config: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
) -> None:
    """Validate an experiment configuration file."""
    try:
        loaded = load_experiment_config(config)
    except (OSError, ValueError, ValidationError) as exc:
        console.print(f"[red]Invalid config:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[green]Config valid[/green]: {loaded.name} "
        f"({len(loaded.solvers)} solver{'s' if len(loaded.solvers) != 1 else ''})"
    )


@app.command("run")
def run_config(
    config: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    run_id: Annotated[str | None, typer.Option("--run-id")] = None,
    artifacts_dir: Annotated[Path | None, typer.Option("--artifacts-dir")] = None,
) -> None:
    """Run a simulation config and write local artifacts."""
    try:
        loaded = load_experiment_config(config)
        artifact_root = artifacts_dir or Path(loaded.storage.artifacts_dir)
        result = PersephoneEngine(artifact_root=artifact_root).run(loaded, run_id=run_id)
    except (OSError, ValueError, ValidationError) as exc:
        console.print(f"[red]Run failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    color = "green" if result.status == "completed" else "red"
    console.print(f"[{color}]{result.status}[/{color}] {result.run_id}")
    console.print(f"Artifacts: {result.artifact_path}")
    console.print(f"Final time: {result.final_time:g}")


@plugins_app.command("list")
def list_plugins() -> None:
    """List installed Persephone plugins."""
    registry = PluginRegistry()
    registry.discover()

    table = Table(title="Installed Persephone plugins")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Paradigm")

    for plugin in registry.list_all():
        table.add_row(plugin["name"], plugin["version"], plugin["paradigm"])

    console.print(table)
    console.print(
        "[yellow]Plugin trust:[/yellow] v2 plugins are trusted Python code; "
        "install only packages you trust."
    )
    if registry.load_errors:
        console.print(f"[yellow]{len(registry.load_errors)} plugin(s) failed to load[/yellow]")


@plugins_app.command("scaffold")
def scaffold_plugin_command(
    name: Annotated[str, typer.Argument()],
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("."),
) -> None:
    """Generate a new trusted-Python plugin package scaffold."""
    try:
        result = scaffold_plugin(name, output_dir)
    except (OSError, ValueError) as exc:
        console.print(f"[red]Scaffold failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Generated[/green] {result.plugin_root}")


@runs_app.command("show")
def show_run(
    run: Annotated[str, typer.Argument()],
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Show run manifest metadata."""
    run_dir = _resolve_run_dir(run, artifacts_dir)
    manifest = _read_json(run_dir / "manifest.json")
    table = Table(title=f"Run {manifest['run_id']}")
    table.add_column("Field")
    table.add_column("Value")
    for key in ["status", "t_current", "config_hash", "engine_version", "sdk_version"]:
        table.add_row(key, str(manifest.get(key)))
    console.print(table)


@runs_app.command("metrics")
def show_metrics(
    run: Annotated[str, typer.Argument()],
    metric: Annotated[str | None, typer.Option("--metric")] = None,
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Print run metric records."""
    run_dir = _resolve_run_dir(run, artifacts_dir)
    records = _read_jsonl(run_dir / "metrics.jsonl")
    if metric is not None:
        records = [record for record in records if record.get("metric") == metric]

    table = Table(title="Run metrics")
    table.add_column("t")
    table.add_column("metric")
    table.add_column("value")
    for record in records:
        table.add_row(str(record.get("t")), str(record.get("metric")), str(record.get("value")))
    console.print(table)


@app.command("replay")
def replay_run(
    run: Annotated[Path, typer.Argument()],
    metrics: Annotated[list[str] | None, typer.Option("--metric")] = None,
) -> None:
    """Replay a completed run as a compact metric timeline."""
    run_dir = _resolve_run_dir(run)
    records = _read_jsonl(run_dir / "metrics.jsonl")
    selected_metrics = set(metrics or _default_metric_names(records))
    records = [record for record in records if record.get("metric") in selected_metrics]

    table = Table(title="Replay")
    table.add_column("t")
    table.add_column("metric")
    table.add_column("value")
    for record in records:
        table.add_row(str(record.get("t")), str(record.get("metric")), str(record.get("value")))
    console.print(table)


@app.command("sweep")
def sweep_config(
    sweep: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Run a scalar parameter sweep from a YAML config."""
    try:
        raw = yaml.safe_load(sweep.read_text(encoding="utf-8"))
        sweep_config = SweepConfig.model_validate(raw)
        manifest = execute_sweep(sweep_config, artifact_root=artifacts_dir)
    except (OSError, ValueError, ValidationError) as exc:
        console.print(f"[red]Sweep failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Sweep {manifest.sweep_id}")
    table.add_column("Run")
    table.add_column("Value")
    table.add_column("Status")
    for child in manifest.child_runs:
        table.add_row(child.run_id, str(child.value), child.status)
    console.print(table)


@app.command("compare")
def compare_runs(
    run_a: Annotated[str, typer.Argument()],
    run_b: Annotated[str, typer.Argument()],
    metric: Annotated[str | None, typer.Option("--metric")] = None,
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Compare two runs for one metric."""
    try:
        records_a = _read_jsonl(_resolve_run_dir(run_a, artifacts_dir) / "metrics.jsonl")
        records_b = _read_jsonl(_resolve_run_dir(run_b, artifacts_dir) / "metrics.jsonl")
        selected_metric = metric or _first_common_metric(records_a, records_b)
        result = compare_metric_records(
            run_a=run_a,
            run_b=run_b,
            metric=selected_metric,
            records_a=records_a,
            records_b=records_b,
        )
    except (OSError, ValueError, RunCatalogError) as exc:
        console.print(f"[red]Compare failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Compare {metric}")
    table.add_column("Run")
    table.add_column("peak")
    table.add_column("final")
    table.add_column("AUC")
    for run_id, summary in result.summaries.items():
        table.add_row(run_id, f"{summary.peak:g}", f"{summary.final:g}", f"{summary.auc:g}")
    console.print(table)


@app.command("export")
def export_run_command(
    run: Annotated[str, typer.Argument()],
    export_format: Annotated[str, typer.Option("--format")] = "csv",
    output: Annotated[Path, typer.Option("--output")] = Path("exports"),
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Export run metrics and events to CSV or Parquet."""
    if export_format not in {"csv", "parquet"}:
        raise typer.BadParameter("--format must be csv or parquet")
    try:
        manifest = export_run(
            artifacts_dir,
            run,
            output_dir=output,
            export_format=cast(Any, export_format),
        )
    except (OSError, ValueError, RunCatalogError) as exc:
        console.print(f"[red]Export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Export {manifest.run_id}")
    table.add_column("Record type")
    table.add_column("Rows")
    table.add_column("Path")
    for exported in manifest.files:
        table.add_row(exported.record_type, str(exported.row_count), str(exported.path))
    console.print(table)


@app.command("api")
def api(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 8787,
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Run the local Persephone API server."""
    import uvicorn

    from persephone.api.app import create_app

    if host not in {"127.0.0.1", "localhost"}:
        console.print("[yellow]Warning:[/yellow] the API is intended for trusted local use only.")

    uvicorn.run(
        create_app(artifact_root=artifacts_dir),
        host=host,
        port=port,
        log_level="info",
    )


@checkpoints_app.command("show")
def show_checkpoint(
    run: Annotated[str, typer.Argument()],
    tick: Annotated[int, typer.Option("--tick", min=0)],
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Show checkpoint metadata for a run."""
    try:
        checkpoint = load_checkpoint(artifacts_dir, run, tick)
    except (OSError, ValueError) as exc:
        console.print(f"[red]Checkpoint unavailable:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Checkpoint {checkpoint.run_id}@{checkpoint.tick}")
    table.add_column("Field")
    table.add_column("Value")
    for key in ["run_id", "tick", "logical_time", "schema_version", "config_hash"]:
        table.add_row(key, str(checkpoint.metadata.get(key)))
    table.add_row("state_arrays", str(len(checkpoint.state)))
    table.add_row("rng_streams", str(len(checkpoint.rng_states)))
    console.print(table)


@fields_app.command("list")
def list_fields_command(
    run: Annotated[str, typer.Argument()],
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """List 2D field artifacts for a run."""
    try:
        fields = list_field_artifacts(artifacts_dir, run)
    except (OSError, ValueError, RunCatalogError) as exc:
        console.print(f"[red]Fields unavailable:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Fields {run}")
    table.add_column("ID")
    table.add_column("Source")
    table.add_column("Shape")
    table.add_column("Dtype")
    for field in fields:
        table.add_row(field.id, field.source, "x".join(map(str, field.dimensions)), field.dtype)
    console.print(table)


@fields_app.command("export")
def export_field_command(
    run: Annotated[str, typer.Argument()],
    field_id: Annotated[str, typer.Argument()],
    output: Annotated[Path, typer.Option("--output")],
    export_format: Annotated[str, typer.Option("--format")] = "csv",
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Export one field artifact to CSV or NPY."""
    if export_format not in {"csv", "npy"}:
        raise typer.BadParameter("--format must be csv or npy")
    try:
        path = export_field_artifact(
            artifacts_dir,
            run,
            field_id,
            output=output,
            export_format=cast(Any, export_format),
        )
    except (OSError, ValueError, RunCatalogError) as exc:
        console.print(f"[red]Field export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Exported[/green] {path}")


@frames_app.command("list")
def list_frames_command(
    run: Annotated[str, typer.Argument()],
    kind: Annotated[str | None, typer.Option("--kind")] = None,
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """List replayable frames for a run."""
    if kind is not None and kind not in {"field", "graph"}:
        raise typer.BadParameter("--kind must be field or graph")
    try:
        frames = list_frames(artifacts_dir, run, kind=cast(Any, kind))
    except (OSError, ValueError, RunCatalogError) as exc:
        console.print(f"[red]Frames unavailable:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Frames {run}")
    table.add_column("ID")
    table.add_column("Kind")
    table.add_column("t")
    table.add_column("Solver")
    table.add_column("Payload")
    for frame in frames.frames:
        table.add_row(
            frame.frame_id,
            frame.kind,
            f"{frame.t:g}",
            frame.solver_id,
            frame.payload_ref.uri,
        )
    console.print(table)


@frames_app.command("show")
def show_frame_command(
    run: Annotated[str, typer.Argument()],
    frame_id: Annotated[str, typer.Argument()],
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Show one replay frame as JSON."""
    try:
        frame = get_frame(artifacts_dir, run, frame_id)
    except (OSError, FrameNotFoundError, ValueError, RunCatalogError) as exc:
        console.print(f"[red]Frame unavailable:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print_json(data=frame)


@frames_app.command("export")
def export_frame_command(
    run: Annotated[str, typer.Argument()],
    frame_id: Annotated[str, typer.Argument()],
    output: Annotated[Path, typer.Option("--output")] = Path("frame.json"),
    export_format: Annotated[str, typer.Option("--format")] = "json",
    artifacts_dir: Annotated[Path, typer.Option("--artifacts-dir")] = Path("runs"),
) -> None:
    """Export one replay frame to JSON, CSV, or NPY."""
    if export_format not in {"json", "csv", "npy"}:
        raise typer.BadParameter("--format must be json, csv, or npy")
    try:
        path = export_frame(
            artifacts_dir,
            run,
            frame_id,
            output=output,
            export_format=cast(Any, export_format),
        )
    except (
        OSError,
        FrameNotFoundError,
        UnsupportedFrameFormatError,
        ValueError,
        RunCatalogError,
    ) as exc:
        console.print(f"[red]Frame export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Exported[/green] {path}")


def _resolve_run_dir(run: str | Path, artifacts_dir: Path = Path("runs")) -> Path:
    try:
        return RunCatalog.scan(artifacts_dir).get(run).path
    except RunCatalogError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _read_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        cast(dict[str, object], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _default_metric_names(records: list[dict[str, object]], limit: int = 3) -> list[str]:
    names: list[str] = []
    for record in records:
        metric = record.get("metric")
        value = record.get("value")
        if (
            isinstance(metric, str)
            and isinstance(value, int | float)
            and not metric.startswith("scheduler.")
            and metric not in names
        ):
            names.append(metric)
        if len(names) >= limit:
            break
    return names


def _first_common_metric(
    records_a: list[dict[str, object]],
    records_b: list[dict[str, object]],
) -> str:
    names_b = {
        str(record["metric"])
        for record in records_b
        if isinstance(record.get("metric"), str) and isinstance(record.get("value"), int | float)
    }
    for record in records_a:
        metric = record.get("metric")
        if (
            isinstance(metric, str)
            and isinstance(record.get("value"), int | float)
            and metric in names_b
            and not metric.startswith("scheduler.")
        ):
            return metric
    raise ValueError("No common numeric metric found; pass --metric explicitly")


if __name__ == "__main__":
    app()
