from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Annotated, cast

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine
from persephone.registry.registry import PluginRegistry

app = typer.Typer(help="Persephone simulation platform CLI.")
plugins_app = typer.Typer(help="Inspect installed simulation plugins.")
runs_app = typer.Typer(help="Inspect completed simulation runs.")
examples_app = typer.Typer(help="Generate example inputs.")
app.add_typer(plugins_app, name="plugins")
app.add_typer(runs_app, name="runs")
app.add_typer(examples_app, name="examples")
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
    if registry.load_errors:
        console.print(f"[yellow]{len(registry.load_errors)} plugin(s) failed to load[/yellow]")


@runs_app.command("show")
def show_run(run: Annotated[Path, typer.Argument()]) -> None:
    """Show run manifest metadata."""
    run_dir = _resolve_run_dir(run)
    manifest = _read_json(run_dir / "manifest.json")
    table = Table(title=f"Run {manifest['run_id']}")
    table.add_column("Field")
    table.add_column("Value")
    for key in ["status", "t_current", "config_hash", "engine_version", "sdk_version"]:
        table.add_row(key, str(manifest.get(key)))
    console.print(table)


@runs_app.command("metrics")
def show_metrics(
    run: Annotated[Path, typer.Argument()],
    metric: Annotated[str | None, typer.Option("--metric")] = None,
) -> None:
    """Print run metric records."""
    run_dir = _resolve_run_dir(run)
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
def replay_run(run: Annotated[Path, typer.Argument()]) -> None:
    """Replay a completed run as a compact metric timeline."""
    run_dir = _resolve_run_dir(run)
    records = _read_jsonl(run_dir / "metrics.jsonl")
    key_metrics = {"susceptible_count", "infected_count", "recovered_count"}
    records = [record for record in records if record.get("metric") in key_metrics]

    table = Table(title="Replay")
    table.add_column("t")
    table.add_column("metric")
    table.add_column("value")
    for record in records:
        table.add_row(str(record.get("t")), str(record.get("metric")), str(record.get("value")))
    console.print(table)


@examples_app.command("generate-sir-network")
def generate_sir_network(
    output: Annotated[Path, typer.Option("--output")],
    nodes: Annotated[int, typer.Option("--nodes", min=2)] = 500,
) -> None:
    """Generate a deterministic synthetic SIR contact graph CSV."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "target", "weight"])
        writer.writeheader()
        for source in range(nodes):
            writer.writerow({"source": source, "target": (source + 1) % nodes, "weight": 1.0})
            writer.writerow({"source": source, "target": (source + 5) % nodes, "weight": 0.35})
    console.print(f"[green]Generated[/green] {output}")


def _resolve_run_dir(run: Path) -> Path:
    if run.exists():
        return run
    candidate = Path("runs") / str(run)
    if candidate.exists():
        return candidate
    raise typer.BadParameter(f"Run path does not exist: {run}")


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


if __name__ == "__main__":
    app()
