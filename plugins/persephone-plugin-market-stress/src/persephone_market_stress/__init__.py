from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import (
    EntityField,
    ExplanationCapability,
    MetricDefinition,
    PluginManifest,
    SemanticManifest,
    StateDefinition,
    ViewCapability,
)

from persephone_market_stress.observer import MarketStressObserver
from persephone_market_stress.renderer import MarketStressRenderer
from persephone_market_stress.solver import MarketStressSolver
from persephone_market_stress.world import MarketStressWorld


class MarketStressPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="market_stress",
            version="0.1.0",
            paradigm="graph",
            world=MarketStressWorld,
            solver=MarketStressSolver,
            observer=MarketStressObserver,
            renderer=MarketStressRenderer,
            bus_reads=[],
            bus_writes=["risk_scores"],
            default_params=default_params(),
            params_schema=params_schema(),
            metrics_schema=metrics_schema(),
            semantics=semantics(),
            sdk_min_version="0.1.0",
        )


def default_params() -> dict[str, Any]:
    return {
        "stress_bias": 0.0,
        "correlation_scale": 1.0,
    }


def params_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "stress_bias": {"type": "number", "minimum": -0.25, "maximum": 0.25},
            "correlation_scale": {"type": "number", "minimum": 0.4, "maximum": 1.5},
        },
    }


def metrics_schema() -> dict[str, Any]:
    return {
        "portfolio_stress_index": {"type": "number"},
        "correlation_pressure": {"type": "number"},
        "active_shocks": {"type": "number"},
        "dispersion_index": {"type": "number"},
    }


def semantics() -> SemanticManifest:
    return SemanticManifest(
        entity_schemas={
            "sector": [
                EntityField(name="label", type="string", label="Sector", required=True),
                EntityField(name="mandate", type="string", label="Mandate", required=True),
                EntityField(
                    name="liquidity_bucket",
                    type="categorical",
                    label="Liquidity bucket",
                    required=True,
                ),
                EntityField(name="stress", type="number", label="Stress score", required=True),
            ]
        },
        state_schema={
            "stable": StateDefinition(
                name="stable",
                kind="categorical",
                label="Stable",
                description="Stress remains contained inside normal ranges.",
            ),
            "watch": StateDefinition(
                name="watch",
                kind="categorical",
                label="Watch",
                description="Cross-sector stress is building and merits monitoring.",
            ),
            "stressed": StateDefinition(
                name="stressed",
                kind="categorical",
                label="Stressed",
                description="The sector has moved into an active stress regime.",
            ),
        },
        metric_schema={
            "portfolio_stress_index": MetricDefinition(
                name="portfolio_stress_index",
                label="Portfolio stress index",
                kind="index",
                unit="idx",
                headline=True,
            ),
            "correlation_pressure": MetricDefinition(
                name="correlation_pressure",
                label="Correlation pressure",
                kind="index",
                unit="idx",
                headline=True,
            ),
            "active_shocks": MetricDefinition(
                name="active_shocks",
                label="Active shocks",
                kind="scalar",
            ),
            "dispersion_index": MetricDefinition(
                name="dispersion_index",
                label="Dispersion index",
                kind="index",
                unit="idx",
            ),
            "stress": MetricDefinition(name="stress", label="Stress score", kind="index"),
            "beta": MetricDefinition(name="beta", label="Beta", kind="ratio"),
            "delta": MetricDefinition(name="delta", label="Step delta", kind="delta"),
        },
        view_capabilities=[
            ViewCapability(kind="matrix", label="Correlation matrix", default=True),
            ViewCapability(kind="network", label="Sector network"),
            ViewCapability(kind="table", label="Sector table"),
            ViewCapability(kind="timeline", label="Stress timeline"),
        ],
        explanation_capabilities=[
            ExplanationCapability(scope="run", label="Run summary"),
            ExplanationCapability(scope="frame", label="Frame summary"),
            ExplanationCapability(scope="selection", label="Sector summary"),
        ],
        default_entity_type="sector",
        preferred_view="matrix",
    )


__all__ = [
    "MarketStressPlugin",
    "MarketStressWorld",
    "MarketStressSolver",
    "MarketStressObserver",
    "MarketStressRenderer",
]
