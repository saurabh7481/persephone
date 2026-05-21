from __future__ import annotations

from persephone_heat_diffusion import HeatDiffusionPlugin
from persephone_sir_epidemic import SIREpidemicPlugin

from persephone.core.frames import FieldFrame, GraphFrame, validate_frame


def test_heat_renderer_emits_field_frame() -> None:
    manifest = HeatDiffusionPlugin.manifest()
    state = manifest.world().init(manifest.default_params, seed=42)

    frames = manifest.renderer().frame(
        state,
        t=0.1,
        run_id="heat-run",
        solver_id="heat_diffusion#0",
        tick=1,
        source="live",
    )

    frame = validate_frame(frames[0])
    assert isinstance(frame, FieldFrame)
    assert frame.field == "temperature"
    assert frame.visualization["kind"] == "heatmap"


def test_sir_renderer_emits_graph_frame() -> None:
    manifest = SIREpidemicPlugin.manifest()
    state = manifest.world().init(manifest.default_params, seed=42)

    frames = manifest.renderer().frame(
        state,
        t=1.0,
        run_id="sir-run",
        solver_id="sir_epidemic#0",
        tick=1,
        source="replay",
    )

    frame = validate_frame(frames[0])
    assert isinstance(frame, GraphFrame)
    assert len(frame.nodes) == len(state["states"])
    assert len(frame.edges) == len(state["edge_sources"])
