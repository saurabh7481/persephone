from __future__ import annotations

from pathlib import Path

import pytest

from persephone.config.load import load_experiment_config


def write_config(tmp_path: Path, body: str) -> Path:
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(body, encoding="utf-8")
    return config_path


def test_loads_valid_experiment_config_and_resolves_local_data_paths(tmp_path: Path) -> None:
    data_path = tmp_path / "edges.csv"
    data_path.write_text("source,target,weight\n0,1,1.0\n", encoding="utf-8")
    config_path = write_config(
        tmp_path,
        """
name: sir_smoke
seed: 42
scheduler:
  t_end: 10
solvers:
  - type: graph
    plugin: sir_epidemic
    version: ">=0.1.0"
    params:
      contact_graph: edges.csv
      p_infect: 0.1
      p_recover: 0.05
      n_nodes: 2
""",
    )

    config = load_experiment_config(config_path)

    assert config.name == "sir_smoke"
    assert config.seed == 42
    assert config.scheduler.t_end == 10
    assert config.solvers[0].params["contact_graph"] == str(data_path)


def test_rejects_missing_solver_list(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
name: invalid
seed: 42
scheduler:
  t_end: 10
""",
    )

    with pytest.raises(ValueError, match="solvers"):
        load_experiment_config(config_path)


def test_rejects_missing_local_data_source(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
name: missing_data
seed: 42
scheduler:
  t_end: 10
solvers:
  - type: graph
    plugin: sir_epidemic
    version: ">=0.1.0"
    params:
      contact_graph: missing.csv
      p_infect: 0.1
""",
    )

    with pytest.raises(ValueError, match="missing.csv"):
        load_experiment_config(config_path)


def test_rejects_invalid_probability_params(tmp_path: Path) -> None:
    data_path = tmp_path / "edges.csv"
    data_path.write_text("source,target,weight\n0,1,1.0\n", encoding="utf-8")
    config_path = write_config(
        tmp_path,
        """
name: invalid_probability
seed: 42
scheduler:
  t_end: 10
solvers:
  - type: graph
    plugin: sir_epidemic
    version: ">=0.1.0"
    params:
      contact_graph: edges.csv
      p_infect: 1.5
""",
    )

    with pytest.raises(ValueError, match="p_infect"):
        load_experiment_config(config_path)


def test_rejects_invalid_coupling_rule_at_config_load(tmp_path: Path) -> None:
    data_path = tmp_path / "edges.csv"
    data_path.write_text("source,target,weight\n0,1,1.0\n", encoding="utf-8")
    config_path = write_config(
        tmp_path,
        """
name: invalid_coupling
seed: 42
scheduler:
  t_end: 10
coupling:
  rules:
    states: not_registered
solvers:
  - type: graph
    plugin: sir_epidemic
    version: ">=0.1.0"
    params:
      contact_graph: edges.csv
      p_infect: 0.1
      p_recover: 0.05
      n_nodes: 2
      initially_infected: [0]
""",
    )

    with pytest.raises(ValueError, match="not_registered"):
        load_experiment_config(config_path)
