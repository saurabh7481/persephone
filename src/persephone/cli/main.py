from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console

from persephone.config.load import load_experiment_config

app = typer.Typer(help="Persephone simulation platform CLI.")
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


if __name__ == "__main__":
    app()
