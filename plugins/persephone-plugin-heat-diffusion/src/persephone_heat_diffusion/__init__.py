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

from persephone_heat_diffusion.observer import HeatObserver
from persephone_heat_diffusion.renderer import HeatRenderer
from persephone_heat_diffusion.solver import HeatSolver
from persephone_heat_diffusion.world import HeatWorld


class HeatDiffusionPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="heat_diffusion",
            version="0.1.0",
            paradigm="pde",
            world=HeatWorld,
            solver=HeatSolver,
            observer=HeatObserver,
            renderer=HeatRenderer,
            bus_reads=[],
            bus_writes=["temperature"],
            default_params=default_params(),
            params_schema=params_schema(),
            metrics_schema=metrics_schema(),
            semantics=semantics(),
            sdk_min_version="0.1.0",
        )


def default_params() -> dict[str, Any]:
    return {
        "width": 12,
        "height": 12,
        "alpha": 0.2,
        "dx": 1.0,
        "dy": 1.0,
        "initial_condition": "center_hotspot",
        "hotspot_temperature": 100.0,
        "ambient_temperature": 0.0,
    }


def params_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["width", "height", "alpha", "dx", "dy"],
        "properties": {
            "width": {"type": "integer", "minimum": 3},
            "height": {"type": "integer", "minimum": 3},
            "alpha": {"type": "number", "exclusiveMinimum": 0},
            "dx": {"type": "number", "exclusiveMinimum": 0},
            "dy": {"type": "number", "exclusiveMinimum": 0},
            "initial_condition": {"type": "string"},
            "initial_condition_path": {"type": "string"},
            "hotspot_temperature": {"type": "number"},
            "ambient_temperature": {"type": "number"},
        },
    }


def metrics_schema() -> dict[str, Any]:
    return {
        "temperature_min": {"type": "number"},
        "temperature_max": {"type": "number"},
        "temperature_mean": {"type": "number"},
        "total_heat": {"type": "number"},
        "center_temperature": {"type": "number"},
    }


def semantics() -> SemanticManifest:
    return SemanticManifest(
        entity_schemas={
            "cell": [
                EntityField(name="row", type="integer", label="Row", required=True),
                EntityField(name="column", type="integer", label="Column", required=True),
                EntityField(
                    name="temperature",
                    type="number",
                    label="Temperature",
                    unit="unitless",
                    required=True,
                ),
            ]
        },
        state_schema={
            "temperature": StateDefinition(
                name="temperature",
                kind="continuous",
                label="Temperature",
                unit="unitless",
            )
        },
        metric_schema={
            "temperature_min": MetricDefinition(name="temperature_min", label="Minimum temperature"),
            "temperature_max": MetricDefinition(name="temperature_max", label="Maximum temperature"),
            "temperature_mean": MetricDefinition(name="temperature_mean", label="Mean temperature"),
            "total_heat": MetricDefinition(name="total_heat", label="Total heat", headline=True),
            "center_temperature": MetricDefinition(
                name="center_temperature",
                label="Center temperature",
                headline=True,
            ),
        },
        view_capabilities=[
            ViewCapability(kind="heatmap", label="Heatmap", default=True),
            ViewCapability(kind="table", label="Cell table"),
        ],
        default_entity_type="cell",
        preferred_view="heatmap",
    )


__all__ = ["HeatDiffusionPlugin", "HeatWorld", "HeatSolver", "HeatObserver", "HeatRenderer"]
