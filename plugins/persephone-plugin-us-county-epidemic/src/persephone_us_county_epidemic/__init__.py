from __future__ import annotations

from importlib.resources import files
from typing import Any

from persephone_sdk.plugin import PluginManifest

from persephone_us_county_epidemic.observer import USCountyObserver
from persephone_us_county_epidemic.renderer import USCountyRenderer
from persephone_us_county_epidemic.solver import USCountySolver
from persephone_us_county_epidemic.world import USCountyWorld


class USCountyEpidemicPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="us_county_epidemic",
            version="0.1.0",
            paradigm="graph",
            world=USCountyWorld,
            solver=USCountySolver,
            observer=USCountyObserver,
            renderer=USCountyRenderer,
            bus_reads=[],
            bus_writes=["states"],
            default_params=default_params(),
            params_schema=params_schema(),
            metrics_schema=metrics_schema(),
            sdk_min_version="0.1.0",
        )


def default_params() -> dict[str, Any]:
    return {
        "data_path": str(
            files("persephone_us_county_epidemic").joinpath("data/county_adjacency2023.txt")
        ),
        "geoid_prefixes": ["06"],
        "initially_infected_geoids": ["06037", "06073"],
        "p_infect": 0.3,
        "p_recover": 0.1,
    }


def params_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "data_path": {"type": "string"},
            "geoid_prefixes": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string", "minLength": 1}},
                ]
            },
            "county_geoids": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string", "minLength": 5}},
                ]
            },
            "initially_infected": {"type": "integer", "minimum": 1},
            "initially_infected_geoids": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string", "minLength": 5}},
                ]
            },
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


__all__ = [
    "USCountyEpidemicPlugin",
    "USCountyWorld",
    "USCountySolver",
    "USCountyObserver",
    "USCountyRenderer",
]
