from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from persephone.config.load import load_experiment_config
from persephone.registry.registry import PluginRegistry

app = typer.Typer(help="Persephone simulation platform CLI.")
plugins_app = typer.Typer(help="Inspect installed simulation plugins.")
app.add_typer(plugins_app, name="plugins")
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


if __name__ == "__main__":
    app()
