from __future__ import annotations

from pathlib import Path

import numpy as np
from persephone_sdk.testing import PluginTestHarness
from persephone_sir_epidemic import SIREpidemicPlugin
from persephone_sir_epidemic.world import SIRWorld


def edge_file(tmp_path: Path) -> Path:
    path = tmp_path / "edges.csv"
    path.write_text("source,target,weight\n0,1,1.0\n1,2,1.0\n2,3,1.0\n", encoding="utf-8")
    return path


def params(tmp_path: Path) -> dict[str, object]:
    return {
        "contact_graph": str(edge_file(tmp_path)),
        "n_nodes": 4,
        "initially_infected": 1,
        "p_infect": 1.0,
        "p_recover": 0.0,
    }


def test_sir_plugin_passes_sdk_harness() -> None:
    PluginTestHarness(SIREpidemicPlugin).run_all()


def test_sir_world_loads_csv_and_initializes_infections(tmp_path: Path) -> None:
    state = SIRWorld().init(params(tmp_path), seed=42)

    assert state["states"].shape == (4,)
    assert state["edge_sources"].tolist() == [0, 1, 2]
    assert state["edge_targets"].tolist() == [1, 2, 3]
    assert state["edge_weights"].tolist() == [1.0, 1.0, 1.0]
    assert int(np.count_nonzero(state["states"] == 1)) == 1


def test_sir_solver_conserves_population_across_steps(tmp_path: Path) -> None:
    manifest = SIREpidemicPlugin.manifest()
    world = manifest.world()
    state = world.init(params(tmp_path), seed=42)
    solver = manifest.solver()

    for _ in range(3):
        state, _ = solver.step(state, dt=1.0, bus=None)
        assert len(state["states"]) == 4
        assert int(np.count_nonzero(np.isin(state["states"], [0, 1, 2]))) == 4


def test_sir_solver_is_deterministic_for_same_seed(tmp_path: Path) -> None:
    manifest = SIREpidemicPlugin.manifest()
    first_state = manifest.world().init(params(tmp_path), seed=7)
    second_state = manifest.world().init(params(tmp_path), seed=7)

    first_solver = manifest.solver()
    second_solver = manifest.solver()
    first_state, _ = first_solver.step(first_state, dt=1.0, bus=None)
    second_state, _ = second_solver.step(second_state, dt=1.0, bus=None)

    np.testing.assert_array_equal(first_state["states"], second_state["states"])
