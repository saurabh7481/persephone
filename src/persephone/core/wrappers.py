from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import PluginManifest
from persephone_sdk.types import StateDict

from persephone.core.bus import InMemoryDataBus


def read_declared_bus_channels(
    manifest: PluginManifest,
    bus: InMemoryDataBus,
) -> dict[str, np.ndarray[Any, Any] | None]:
    return {channel: bus.read(channel) for channel in manifest.bus_reads}


def write_declared_bus_channels(
    manifest: PluginManifest,
    state: StateDict,
    bus: InMemoryDataBus,
    *,
    solver_id: str,
    tick: int,
    logical_time: float | None = None,
) -> None:
    undeclared = sorted(set(state) - set(manifest.bus_writes))
    if undeclared:
        raise ValueError("State contains undeclared bus write channel(s): " + ", ".join(undeclared))

    for channel in manifest.bus_writes:
        if channel in state:
            bus.write(
                channel,
                state[channel],
                solver_id=solver_id,
                tick=tick,
                logical_time=logical_time,
            )
