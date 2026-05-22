from __future__ import annotations

from persephone_dependency_workflow import DependencyWorkflowPlugin
from persephone_sdk.testing import PluginTestHarness


def test_dependency_workflow_plugin_passes_sdk_harness() -> None:
    PluginTestHarness(DependencyWorkflowPlugin).run_all()


def test_dependency_workflow_plugin_declares_hierarchy_first_semantics() -> None:
    manifest = DependencyWorkflowPlugin.manifest()

    assert manifest.semantics.preferred_view == "hierarchy"
    assert manifest.semantics.default_entity_type == "service"
    assert [capability.kind for capability in manifest.semantics.view_capabilities] == [
        "hierarchy",
        "table",
        "timeline",
        "network",
    ]
    assert {capability.scope for capability in manifest.semantics.explanation_capabilities} == {
        "run",
        "frame",
        "selection",
    }
