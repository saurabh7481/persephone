from __future__ import annotations

from persephone_market_stress import MarketStressPlugin
from persephone_sdk.testing import PluginTestHarness


def test_market_stress_plugin_passes_sdk_harness() -> None:
    PluginTestHarness(MarketStressPlugin).run_all()


def test_market_stress_plugin_declares_matrix_first_semantics() -> None:
    manifest = MarketStressPlugin.manifest()

    assert manifest.semantics.preferred_view == "matrix"
    assert manifest.semantics.default_entity_type == "sector"
    assert [capability.kind for capability in manifest.semantics.view_capabilities] == [
        "matrix",
        "network",
        "table",
        "timeline",
    ]
    assert {capability.scope for capability in manifest.semantics.explanation_capabilities} == {
        "run",
        "frame",
        "selection",
    }
