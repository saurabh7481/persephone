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

from persephone_dependency_workflow.observer import DependencyWorkflowObserver
from persephone_dependency_workflow.renderer import DependencyWorkflowRenderer
from persephone_dependency_workflow.solver import DependencyWorkflowSolver
from persephone_dependency_workflow.world import DependencyWorkflowWorld


class DependencyWorkflowPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="dependency_workflow",
            version="0.1.0",
            paradigm="graph",
            world=DependencyWorkflowWorld,
            solver=DependencyWorkflowSolver,
            observer=DependencyWorkflowObserver,
            renderer=DependencyWorkflowRenderer,
            bus_reads=[],
            bus_writes=["service_risk", "review_backlog"],
            default_params=default_params(),
            params_schema=params_schema(),
            metrics_schema=metrics_schema(),
            semantics=semantics(),
            sdk_min_version="0.1.0",
        )


def default_params() -> dict[str, Any]:
    return {
        "risk_bias": 0.0,
        "backlog_bias": 0.0,
    }


def params_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "risk_bias": {"type": "number", "minimum": -0.25, "maximum": 0.25},
            "backlog_bias": {"type": "number", "minimum": -2.0, "maximum": 6.0},
        },
    }


def metrics_schema() -> dict[str, Any]:
    return {
        "delivery_risk_index": {"type": "number"},
        "blocked_items": {"type": "number"},
        "review_backlog": {"type": "number"},
        "critical_path_pressure": {"type": "number"},
    }


def semantics() -> SemanticManifest:
    return SemanticManifest(
        entity_schemas={
            "service": [
                EntityField(name="label", type="string", label="Service", required=True),
                EntityField(name="owner", type="string", label="Owner", required=True),
                EntityField(name="tier", type="categorical", label="Tier", required=True),
                EntityField(
                    name="review_backlog",
                    type="number",
                    label="Review backlog",
                    unit="items",
                    required=True,
                ),
            ]
        },
        state_schema={
            "healthy": StateDefinition(
                name="healthy",
                kind="categorical",
                label="Healthy",
                description="Delivery risk is contained.",
            ),
            "watch": StateDefinition(
                name="watch",
                kind="categorical",
                label="Watch",
                description="The service is accumulating workflow pressure.",
            ),
            "blocked": StateDefinition(
                name="blocked",
                kind="categorical",
                label="Blocked",
                description="The service is a critical blocker on the dependency path.",
            ),
        },
        metric_schema={
            "delivery_risk_index": MetricDefinition(
                name="delivery_risk_index",
                label="Delivery risk index",
                kind="index",
                unit="idx",
                headline=True,
            ),
            "blocked_items": MetricDefinition(
                name="blocked_items",
                label="Blocked items",
                kind="scalar",
                headline=True,
            ),
            "review_backlog": MetricDefinition(
                name="review_backlog",
                label="Review backlog",
                kind="scalar",
                unit="items",
            ),
            "critical_path_pressure": MetricDefinition(
                name="critical_path_pressure",
                label="Critical path pressure",
                kind="index",
                unit="idx",
            ),
            "service_risk": MetricDefinition(
                name="service_risk",
                label="Service risk",
                kind="index",
            ),
            "risk_delta": MetricDefinition(name="risk_delta", label="Risk delta", kind="delta"),
        },
        view_capabilities=[
            ViewCapability(kind="hierarchy", label="Dependency hierarchy", default=True),
            ViewCapability(kind="table", label="Service table"),
            ViewCapability(kind="timeline", label="Workflow timeline"),
            ViewCapability(kind="network", label="Dependency network"),
        ],
        explanation_capabilities=[
            ExplanationCapability(scope="run", label="Run summary"),
            ExplanationCapability(scope="frame", label="Frame summary"),
            ExplanationCapability(scope="selection", label="Service summary"),
        ],
        default_entity_type="service",
        preferred_view="hierarchy",
    )


__all__ = [
    "DependencyWorkflowPlugin",
    "DependencyWorkflowWorld",
    "DependencyWorkflowSolver",
    "DependencyWorkflowObserver",
    "DependencyWorkflowRenderer",
]
