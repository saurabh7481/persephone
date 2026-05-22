from __future__ import annotations

import pytest

from persephone.config.schema import core_record_json_schemas
from persephone.core.frames import FieldFrame, FramePayloadRef, GraphFrame, validate_frame


def test_field_frame_validates_inline_payload() -> None:
    frame = validate_frame(
        {
            "kind": "field",
            "run_id": "run-a",
            "frame_id": "field-001",
            "t": 0.5,
            "tick": 5,
            "solver_id": "solver#0",
            "source": "live",
            "field": "state",
            "shape": [2, 2],
            "dtype": "float64",
            "bounds": {"min": 0.0, "max": 1.0},
            "units": "unitless",
            "visualization": {"kind": "heatmap"},
            "values": [0.0, 0.5, 0.75, 1.0],
        }
    )

    assert isinstance(frame, FieldFrame)
    assert frame.shape == (2, 2)


def test_field_frame_rejects_mismatched_inline_payload() -> None:
    with pytest.raises(ValueError, match="shape"):
        FieldFrame(
            run_id="run-a",
            frame_id="bad",
            t=0.0,
            tick=0,
            solver_id="solver#0",
            source="live",
            field="state",
            shape=(2, 2),
            dtype="float64",
            bounds={"min": 0.0, "max": 1.0},
            values=[1.0, 2.0],
        )


def test_graph_frame_validates_nodes_and_edges() -> None:
    frame = validate_frame(
        {
            "kind": "graph",
            "run_id": "run-a",
            "frame_id": "graph-001",
            "t": 1.0,
            "tick": 1,
            "solver_id": "solver#0",
            "source": "replay",
            "nodes": [{"id": "0", "state": "active"}],
            "edges": [{"source": "0", "target": "1", "weight": 0.5}],
        }
    )

    assert isinstance(frame, GraphFrame)
    assert frame.nodes[0].id == "0"


def test_graph_frame_accepts_rich_metadata_and_visualization_hints() -> None:
    frame = validate_frame(
        {
            "kind": "graph",
            "run_id": "run-rich",
            "frame_id": "graph-rich-001",
            "t": 2.0,
            "tick": 2,
            "solver_id": "solver#0",
            "source": "live",
            "nodes": [
                {
                    "id": "alpha",
                    "label": "Alpha region",
                    "group": "west",
                    "lat": 34.05,
                    "lon": -118.24,
                    "metrics": {"load": 0.82},
                    "attrs": {"priority": "high"},
                    "state": "active",
                }
            ],
            "edges": [
                {
                    "source": "alpha",
                    "target": "beta",
                    "weight": 0.7,
                    "kind": "dependency",
                    "directed": True,
                    "attrs": {"mode": "critical"},
                }
            ],
            "visualization": {
                "layout_hint": "geographic",
                "coordinate_system": "geo",
                "preferred_view": "map_network",
                "legend": {"active": "#ff6600"},
                "selection_schema": {"type": "node"},
                "density_hint": "sparse",
            },
        }
    )

    assert isinstance(frame, GraphFrame)
    assert frame.nodes[0].label == "Alpha region"
    assert frame.nodes[0].metrics == {"load": 0.82}
    assert frame.edges[0].directed is True
    assert frame.visualization.preferred_view == "map_network"


def test_frame_schema_export_contains_frame_models() -> None:
    schemas = core_record_json_schemas()

    assert "FieldFrame" in schemas
    assert "GraphFrame" in schemas
    assert "FrameIndex" in schemas
    assert "FramePayloadRef" in schemas


def test_field_frame_accepts_payload_ref_for_large_frames() -> None:
    frame = FieldFrame(
        run_id="run-a",
        frame_id="ref",
        t=0.0,
        tick=0,
        solver_id="solver#0",
        source="replay",
        field="state",
        shape=(200, 200),
        dtype="float64",
        bounds={"min": 0.0, "max": 1.0},
        payload_ref=FramePayloadRef(uri="frames/ref.npz", format="npz"),
    )

    assert frame.payload_ref is not None
