from __future__ import annotations

from importlib.resources import files
from typing import Any

from persephone_sdk.plugin import PluginManifest

from persephone_sir_epidemic.observer import SIRObserver
from persephone_sir_epidemic.renderer import SIRRenderer
from persephone_sir_epidemic.solver import SIRSolver
from persephone_sir_epidemic.world import SIRWorld


class SIREpidemicPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="sir_epidemic",
            version="0.1.0",
            paradigm="graph",
            world=SIRWorld,
            solver=SIRSolver,
            observer=SIRObserver,
            renderer=SIRRenderer,
            bus_reads=[],
            bus_writes=["states"],
            default_params=default_params(),
            params_schema=params_schema(),
            metrics_schema=metrics_schema(),
            sdk_min_version="0.1.0",
        )


def default_params() -> dict[str, Any]:
    return {
        "contact_graph": str(files("persephone_sir_epidemic").joinpath("data/default_edges.csv")),
        "n_nodes": 6,
        "initially_infected": 1,
        "p_infect": 0.35,
        "p_recover": 0.1,
    }


def params_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["contact_graph", "n_nodes", "initially_infected", "p_infect", "p_recover"],
        "properties": {
            "contact_graph": {"type": "string"},
            "n_nodes": {"type": "integer", "minimum": 1},
            "initially_infected": {"type": ["integer", "array"], "minimum": 1},
            "p_infect": {"type": "number", "minimum": 0, "maximum": 1},
            "p_recover": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


def metrics_schema() -> dict[str, Any]:
    return {
        "susceptible_count": {"type": "number"},
        "infected_count": {"type": "number"},
        "recovered_count": {"type": "number"},
        "new_infections": {"type": "number"},
        "new_recoveries": {"type": "number"},
        "r_effective_estimate": {"type": "number"},
    }


__all__ = ["SIREpidemicPlugin", "SIRWorld", "SIRSolver", "SIRObserver", "SIRRenderer"]
