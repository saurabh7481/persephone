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

from persephone_river_flood.observer import RiverFloodObserver
from persephone_river_flood.renderer import RiverFloodRenderer
from persephone_river_flood.solver import RiverFloodSolver
from persephone_river_flood.world import RiverFloodWorld


class RiverFloodPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="river_flood",
            version="0.1.0",
            paradigm="graph",
            world=RiverFloodWorld,
            solver=RiverFloodSolver,
            observer=RiverFloodObserver,
            renderer=RiverFloodRenderer,
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
        "event_preset": "spring_snowmelt",
        "precipitation_cms": 500.0,
        "precipitation_duration_hours": 24,
        "routing_k": 0.35,
        "custom_injection_stations": [],
    }


def _params_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "event_preset": {"type": "string", "enum": ["spring_snowmelt", "gulf_hurricane", "custom"]},
            "precipitation_cms": {"type": "number", "minimum": 0},
            "precipitation_duration_hours": {"type": "integer", "minimum": 1},
            "routing_k": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
            "custom_injection_stations": {"type": "array", "items": {"type": "integer", "minimum": 0}},
        },
    }


def _metrics_schema() -> dict[str, Any]:
    return {
        "stations_flooding": {"type": "number"},
        "stations_watch": {"type": "number"},
        "total_excess_flow_cms": {"type": "number"},
        "peak_flow_cms": {"type": "number"},
        "flood_front_km": {"type": "number"},
    }


def _semantics() -> SemanticManifest:
    return SemanticManifest(
        entity_schemas={
            "gauge": [
                EntityField(name="name", type="string", label="Station Name", required=True),
                EntityField(name="flow_cms", type="number", label="Flow (m³/s)", required=True),
            ]
        },
        state_schema={
            "flood_status": StateDefinition(
                name="flood_status", kind="categorical", label="Flood Status", unit="category"
            )
        },
        metric_schema={
            "stations_flooding": MetricDefinition(
                name="stations_flooding", label="Stations at flood stage", headline=True
            ),
            "stations_watch": MetricDefinition(name="stations_watch", label="Stations at watch"),
            "total_excess_flow_cms": MetricDefinition(
                name="total_excess_flow_cms", label="Total excess flow (m³/s)", headline=True
            ),
            "peak_flow_cms": MetricDefinition(name="peak_flow_cms", label="Peak flow (m³/s)"),
            "flood_front_km": MetricDefinition(
                name="flood_front_km", label="Flood front (river km)"
            ),
        },
        view_capabilities=[
            ViewCapability(kind="map_network", label="Mississippi flood map", default=True),
            ViewCapability(kind="network", label="River network"),
        ],
        default_entity_type="gauge",
        preferred_view="map_network",
    )


__all__ = [
    "RiverFloodPlugin",
    "RiverFloodWorld",
    "RiverFloodSolver",
    "RiverFloodObserver",
    "RiverFloodRenderer",
]
