from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import (
    EntityField,
    MetricDefinition,
    PluginManifest,
    SemanticManifest,
    StateDefinition,
    ViewCapability,
)

from persephone_airline_delay.observer import AirlineDelayObserver
from persephone_airline_delay.renderer import AirlineDelayRenderer
from persephone_airline_delay.solver import AirlineDelaySolver
from persephone_airline_delay.world import AirlineDelayWorld


class AirlineDelayPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="airline_delay",
            version="0.1.0",
            paradigm="graph",
            world=AirlineDelayWorld,
            solver=AirlineDelaySolver,
            observer=AirlineDelayObserver,
            renderer=AirlineDelayRenderer,
            bus_reads=[],
            bus_writes=[],
            default_params=_default_params(),
            params_schema=_params_schema(),
            metrics_schema=_metrics_schema(),
            semantics=_semantics(),
            sdk_min_version="0.1.0",
        )


def _default_params() -> dict[str, Any]:
    return {
        "initial_airports": ["JFK", "LHR", "DXB"],
        "initial_delay_minutes": 180.0,
        "propagation_factor": 0.3,
        "recovery_rate": 0.15,
    }


def _params_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "initial_airports": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string", "minLength": 3}},
                ]
            },
            "initial_delay_minutes": {"type": "number", "minimum": 0},
            "propagation_factor": {"type": "number", "minimum": 0, "maximum": 1},
            "recovery_rate": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


def _metrics_schema() -> dict[str, Any]:
    return {
        "delayed_airports": {"type": "number"},
        "disrupted_airports": {"type": "number"},
        "total_delay_minutes": {"type": "number"},
        "max_delay_minutes": {"type": "number"},
        "cascade_reach": {"type": "number"},
    }


def _semantics() -> SemanticManifest:
    return SemanticManifest(
        entity_schemas={
            "airport": [
                EntityField(name="iata", type="string", label="IATA Code", required=True),
                EntityField(name="delay_minutes", type="number", label="Delay (min)", required=True),
            ]
        },
        state_schema={
            "status": StateDefinition(
                name="status", kind="categorical", label="Delay Status", unit="category"
            )
        },
        metric_schema={
            "delayed_airports": MetricDefinition(name="delayed_airports", label="Delayed airports"),
            "disrupted_airports": MetricDefinition(
                name="disrupted_airports", label="Disrupted airports", headline=True
            ),
            "total_delay_minutes": MetricDefinition(
                name="total_delay_minutes", label="Total delay (min)", headline=True
            ),
            "max_delay_minutes": MetricDefinition(
                name="max_delay_minutes", label="Peak delay (min)"
            ),
            "cascade_reach": MetricDefinition(
                name="cascade_reach", label="Airports ever delayed"
            ),
        },
        view_capabilities=[
            ViewCapability(kind="map_network", label="Global delay map", default=True),
            ViewCapability(kind="network", label="Route network"),
        ],
        default_entity_type="airport",
        preferred_view="map_network",
    )


__all__ = [
    "AirlineDelayPlugin",
    "AirlineDelayWorld",
    "AirlineDelaySolver",
    "AirlineDelayObserver",
    "AirlineDelayRenderer",
]
