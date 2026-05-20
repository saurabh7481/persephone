from __future__ import annotations

import json
from pathlib import Path

from persephone.config.load import load_experiment_config
from persephone.sweeps import SweepConfig, execute_sweep, generate_sweep_configs


def test_generate_sweep_configs_sets_dotted_scalar_path() -> None:
    base_config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    sweep = SweepConfig(
        sweep_id="infectivity-sweep",
        name="Infectivity sweep",
        base_config=base_config,
        parameter="solvers[0].params.p_infect",
        values=[0.2, 0.4],
    )

    generated = generate_sweep_configs(sweep)

    assert [item.run_id for item in generated] == [
        "infectivity-sweep-001",
        "infectivity-sweep-002",
    ]
    assert generated[0].config.solvers[0].params["p_infect"] == 0.2
    assert generated[1].config.solvers[0].params["p_infect"] == 0.4
    assert base_config.solvers[0].params["p_infect"] != 0.2


def test_execute_sweep_writes_manifest_and_links_child_runs(tmp_path: Path) -> None:
    base_config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    sweep = SweepConfig(
        sweep_id="recover-sweep",
        name="Recovery sweep",
        base_config=base_config,
        parameter="solvers[0].params.p_recover",
        values=[0.05, 0.1],
    )

    manifest = execute_sweep(sweep, artifact_root=tmp_path / "runs")

    assert manifest.sweep_id == "recover-sweep"
    assert [child.run_id for child in manifest.child_runs] == [
        "recover-sweep-001",
        "recover-sweep-002",
    ]
    assert (tmp_path / "runs" / "recover-sweep" / "sweep.json").exists()

    child_manifest_path = tmp_path / "runs" / "recover-sweep-001" / "manifest.json"
    child_manifest = json.loads(child_manifest_path.read_text(encoding="utf-8"))
    assert child_manifest["sweep_id"] == "recover-sweep"
    assert child_manifest["sweep_parameter"] == "solvers[0].params.p_recover"
    assert child_manifest["sweep_value"] == 0.05
