from __future__ import annotations

import json
from pathlib import Path

import pytest

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine
from persephone.frames import get_frame, list_frames


def test_engine_persists_frame_index_and_inline_payloads(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/heat_diffusion.yaml")
    config.scheduler.t_end = 0.2
    config.visualization.emit_every = 0.1

    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(config, run_id="frame-store")

    assert result.status == "completed"
    frame_root = tmp_path / "runs" / "frame-store" / "frames"
    index = json.loads((frame_root / "index.json").read_text(encoding="utf-8"))
    payload_lines = (frame_root / "frames.jsonl").read_text(encoding="utf-8").splitlines()
    manifest = json.loads(
        (tmp_path / "runs" / "frame-store" / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["frame_artifacts_path"] == "frames/index.json"
    assert index["run_id"] == "frame-store"
    assert [frame["kind"] for frame in index["frames"]] == ["field", "field"]
    assert len(payload_lines) == 2
    assert json.loads(payload_lines[0])["values"]

    frames = list_frames(tmp_path / "runs", "frame-store", kind="field")
    assert frames.metadata.frame_count == 2
    assert frames.frames[0].payload_ref is not None

    frame = get_frame(tmp_path / "runs", "frame-store", frames.frames[0].frame_id)
    assert frame["kind"] == "field"
    assert frame["values"]


def test_large_field_frames_are_stored_as_npz_payload_refs(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/heat_diffusion.yaml")
    config.scheduler.t_end = 0.1
    config.visualization.emit_every = 0.1
    config.visualization.inline_frame_max_values = 4

    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(config, run_id="large-frame")

    assert result.status == "completed"
    frame = get_frame(tmp_path / "runs", "large-frame", "heat_diffusion#0:temperature:000001")

    assert frame["kind"] == "field"
    assert frame["payload_ref"]["format"] == "npz"
    assert (tmp_path / "runs" / "large-frame" / frame["payload_ref"]["uri"]).exists()
    assert frame["values"]


def test_large_heat_demo_preset_emits_multiple_replay_frames(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/heat_diffusion_large.yaml")
    config.scheduler.t_end = 1.0
    config.scheduler.demo_delay_ms_per_tick = 0

    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(
        config,
        run_id="large-heat-demo",
    )

    assert result.status == "completed"
    frames = list_frames(tmp_path / "runs", "large-heat-demo", kind="field")
    assert frames.metadata.frame_count == 4
    assert [frame.t for frame in frames.frames] == pytest.approx([0.25, 0.5, 0.75, 1.0])
    frame = get_frame(tmp_path / "runs", "large-heat-demo", frames.frames[0].frame_id)
    assert frame["shape"] == [96, 96]
