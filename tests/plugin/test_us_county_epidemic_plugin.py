from __future__ import annotations

from pathlib import Path

import numpy as np
from persephone_sdk.testing import PluginTestHarness
from persephone_us_county_epidemic import USCountyEpidemicPlugin
from persephone_us_county_epidemic.dataset import load_county_graph
from persephone_us_county_epidemic.world import USCountyWorld


def test_us_county_epidemic_plugin_passes_sdk_harness() -> None:
    PluginTestHarness(USCountyEpidemicPlugin).run_all()


def test_dataset_loader_filters_real_county_graph_to_california() -> None:
    manifest = USCountyEpidemicPlugin.manifest()
    graph = load_county_graph(str(manifest.default_params["data_path"]), manifest.default_params)

    assert len(graph.geoids) == 58
    assert graph.geoids[0] == "06001"
    assert "06037" in graph.geoids
    assert len(graph.edge_sources) == len(graph.edge_targets)
    assert len(graph.edge_sources) > 80


def test_world_initializes_from_small_raw_adjacency_file(tmp_path: Path) -> None:
    data_path = tmp_path / "county_adjacency.txt"
    data_path.write_text(
        "\n".join(
            [
                "County Name|County GEOID|Neighbor Name|Neighbor GEOID",
                "Alpha County, CA|06001|Alpha County, CA|06001",
                "Alpha County, CA|06001|Beta County, CA|06013",
                "Beta County, CA|06013|Alpha County, CA|06001",
                "Beta County, CA|06013|Beta County, CA|06013",
                "Beta County, CA|06013|Gamma County, NV|32003",
                "Gamma County, NV|32003|Beta County, CA|06013",
            ]
        ),
        encoding="utf-8",
    )

    state = USCountyWorld().init(
        {
            "data_path": str(data_path),
            "county_geoids": ["06001", "06013"],
            "initially_infected_geoids": ["06013"],
            "p_infect": 0.5,
            "p_recover": 0.1,
        },
        seed=7,
    )

    assert state["node_geoids"].tolist() == [6001, 6013]
    assert state["edge_sources"].tolist() == [0]
    assert state["edge_targets"].tolist() == [1]
    assert int(np.count_nonzero(state["states"] == 1)) == 1


def test_solver_events_use_county_geoids() -> None:
    manifest = USCountyEpidemicPlugin.manifest()
    world = manifest.world()
    state = world.init(
        {
            **manifest.default_params,
            "county_geoids": ["06037", "06059"],
            "initially_infected_geoids": ["06037"],
            "p_infect": 1.0,
            "p_recover": 0.0,
        },
        seed=42,
    )
    solver = manifest.solver()
    state, _ = solver.step(state, dt=1.0, bus=None)

    assert state["states"].tolist() == [1, 1]
    assert solver.last_events[0]["entity_id"] == "06059"
    assert solver.last_events[0]["source_id"] == "06037"
