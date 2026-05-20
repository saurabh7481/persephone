from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from typer.testing import CliRunner

from persephone.cli.main import app
from persephone.core.bus import BusChannelSchema, InMemoryDataBus


def test_checkpoints_show_prints_checkpoint_metadata(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "runs" / "run-a" / "checkpoints" / "000001"
    checkpoint_dir.mkdir(parents=True)
    np.savez(checkpoint_dir / "state.npz", value=np.array([1.0]))
    bus = InMemoryDataBus(
        run_id="run-a",
        schemas={"value": BusChannelSchema(name="value", dtype="float64", shape=(1,))},
    )
    (checkpoint_dir / "bus.json").write_text(
        json.dumps(bus.snapshot()),
        encoding="utf-8",
    )
    (checkpoint_dir / "rng.json").write_text(
        json.dumps({"solver#0": {"bit_generator": "PCG64"}}),
        encoding="utf-8",
    )
    (checkpoint_dir / "checkpoint.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "run-a",
                "tick": 1,
                "logical_time": 1.0,
                "engine_version": "0.1.0",
                "plugin_versions": {"demo": "0.1.0"},
                "config_hash": "abc",
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["checkpoints", "show", "run-a", "--tick", "1", "--artifacts-dir", str(tmp_path / "runs")],
    )

    assert result.exit_code == 0
    assert "run-a" in result.output
    assert "logical_time" in result.output
