from __future__ import annotations

from pathlib import Path

from persephone_us_county_epidemic import USCountyEpidemicPlugin

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine
from persephone.registry.registry import PluginRegistry


def test_example_us_county_config_validates() -> None:
    config = load_experiment_config("configs/examples/us_county_epidemic.yaml")

    assert config.name == "us_county_epidemic_california"
    assert config.solvers[0].plugin == "us_county_epidemic"
    assert config.solvers[0].params["geoid_prefixes"] == ["06"]


class _EntryPoint:
    name = "us_county_epidemic"

    def load(self) -> type[USCountyEpidemicPlugin]:
        return USCountyEpidemicPlugin


def test_example_us_county_run_completes(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/us_county_epidemic.yaml")
    config.storage.artifacts_dir = str(tmp_path / "runs")
    config.scheduler.t_end = 6

    registry = PluginRegistry(entry_points_provider=lambda: [_EntryPoint()])
    result = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs").run(
        config,
        run_id="us-county-example",
    )

    assert result.status == "completed"
    assert result.final_time == 6.0
    assert result.metric_summary["infected_count"] >= 0
