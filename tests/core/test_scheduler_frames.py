from __future__ import annotations

from pathlib import Path
from typing import Any

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine


def test_scheduler_emits_frames_at_visualization_cadence(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/heat_diffusion.yaml")
    config.scheduler.t_end = 0.3
    config.visualization.emit_every = 0.2
    records: list[tuple[str, dict[str, Any]]] = []

    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(
        config,
        run_id="frame-cadence",
        record_callback=lambda kind, record: records.append((kind, record)),
    )

    assert result.status == "completed"
    frames = [record for kind, record in records if kind == "frame"]
    metrics = [record for kind, record in records if kind == "metric"]
    assert [frame["t"] for frame in frames] == [0.2]
    assert metrics
