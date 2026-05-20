from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from persephone.core.bus import InMemoryDataBus


@dataclass(frozen=True)
class LoadedCheckpoint:
    run_id: str
    tick: int
    metadata: dict[str, Any]
    state: dict[str, np.ndarray[Any, Any]]
    bus: InMemoryDataBus
    rng_states: dict[str, Any]


def load_checkpoint(artifact_root: str | Path, run_id: str, tick: int) -> LoadedCheckpoint:
    checkpoint_dir = Path(artifact_root) / run_id / "checkpoints" / f"{tick:06d}"
    metadata = _read_json(checkpoint_dir / "checkpoint.json")
    bus_snapshot = _read_json(checkpoint_dir / "bus.json")
    rng_states = _read_json(checkpoint_dir / "rng.json")

    with np.load(checkpoint_dir / "state.npz") as loaded:
        state = {key: loaded[key].copy() for key in loaded.files}

    return LoadedCheckpoint(
        run_id=run_id,
        tick=tick,
        metadata=metadata,
        state=state,
        bus=InMemoryDataBus.from_snapshot(bus_snapshot),
        rng_states=rng_states,
    )


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
