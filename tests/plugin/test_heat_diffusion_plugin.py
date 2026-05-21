from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from persephone_heat_diffusion import HeatDiffusionPlugin
from persephone_sdk.testing import PluginTestHarness


def test_heat_diffusion_plugin_passes_sdk_harness() -> None:
    PluginTestHarness(HeatDiffusionPlugin).run_all()


def test_heat_solver_conserves_total_heat_for_neumann_boundaries() -> None:
    manifest = HeatDiffusionPlugin.manifest()
    state = manifest.world().init(
        {
            "width": 10,
            "height": 10,
            "alpha": 0.2,
            "dx": 1.0,
            "dy": 1.0,
            "initial_condition": "center_hotspot",
            "hotspot_temperature": 100.0,
            "ambient_temperature": 0.0,
        },
        seed=42,
    )
    solver = manifest.solver()
    initial_heat = float(np.sum(state["temperature"]))

    for _ in range(5):
        state, elapsed = solver.step(state, dt=0.1, bus=None)
        assert elapsed == 0.1

    assert float(np.sum(state["temperature"])) == pytest.approx(initial_heat)
    assert np.all(np.isfinite(state["temperature"]))


def test_heat_solver_rejects_cfl_unsafe_dt() -> None:
    manifest = HeatDiffusionPlugin.manifest()
    state = manifest.world().init(manifest.default_params, seed=42)
    solver = manifest.solver()

    with pytest.raises(ValueError, match="CFL"):
        solver.step(state, dt=10.0, bus=None)


def test_heat_initial_condition_generator_writes_npy(tmp_path: Path) -> None:
    from persephone_heat_diffusion.initial_conditions import write_initial_condition

    output = write_initial_condition(tmp_path / "field.npy", width=8, height=6, seed=7)

    field = np.load(output)
    assert field.shape == (6, 8)
    assert float(field.max()) > float(field.mean())
