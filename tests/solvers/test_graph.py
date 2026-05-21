from __future__ import annotations

from pathlib import Path

import numpy as np
from persephone_sir_epidemic.model import INFECTED, RECOVERED, SUSCEPTIBLE, sir_step

from persephone.solvers.graph import ContactGraph


def write_edges(tmp_path: Path) -> Path:
    path = tmp_path / "edges.csv"
    path.write_text("source,target,weight\n0,1,0.5\n1,2,1.0\n", encoding="utf-8")
    return path


def test_contact_graph_loads_weighted_undirected_edges(tmp_path: Path) -> None:
    graph = ContactGraph.from_csv(write_edges(tmp_path), n_nodes=3)

    assert graph.n_nodes == 3
    assert graph.neighbors(0) == [(1, 0.5)]
    assert graph.neighbors(1) == [(0, 0.5), (2, 1.0)]
    assert graph.neighbors(2) == [(1, 1.0)]


def test_no_infection_when_probability_is_zero(tmp_path: Path) -> None:
    graph = ContactGraph.from_csv(write_edges(tmp_path), n_nodes=3)
    states = np.array([INFECTED, SUSCEPTIBLE, SUSCEPTIBLE], dtype=np.int8)

    result = sir_step(
        graph=graph,
        states=states,
        p_infect=0.0,
        p_recover=0.0,
        rng=np.random.default_rng(1),
        t=1.0,
    )

    np.testing.assert_array_equal(result.states, states)
    assert result.events == []


def test_guaranteed_infection_uses_previous_state_only(tmp_path: Path) -> None:
    path = tmp_path / "unit_edges.csv"
    path.write_text("source,target,weight\n0,1,1.0\n1,2,1.0\n", encoding="utf-8")
    graph = ContactGraph.from_csv(path, n_nodes=3)
    states = np.array([INFECTED, SUSCEPTIBLE, SUSCEPTIBLE], dtype=np.int8)

    result = sir_step(
        graph=graph,
        states=states,
        p_infect=1.0,
        p_recover=0.0,
        rng=np.random.default_rng(1),
        t=1.0,
    )

    np.testing.assert_array_equal(result.states, np.array([INFECTED, INFECTED, SUSCEPTIBLE]))
    assert [event["event"] for event in result.events] == ["infection"]
    assert result.events[0]["source_id"] == 0
    assert result.events[0]["entity_id"] == 1


def test_recovery_events_and_population_conservation(tmp_path: Path) -> None:
    graph = ContactGraph.from_csv(write_edges(tmp_path), n_nodes=3)
    states = np.array([INFECTED, SUSCEPTIBLE, RECOVERED], dtype=np.int8)

    result = sir_step(
        graph=graph,
        states=states,
        p_infect=0.0,
        p_recover=1.0,
        rng=np.random.default_rng(1),
        t=1.0,
    )

    assert int(np.count_nonzero(result.states == SUSCEPTIBLE)) == 1
    assert int(np.count_nonzero(result.states == INFECTED)) == 0
    assert int(np.count_nonzero(result.states == RECOVERED)) == 2
    assert result.events[0]["event"] == "recovery"


def test_sir_step_is_deterministic_with_same_seed(tmp_path: Path) -> None:
    graph = ContactGraph.from_csv(write_edges(tmp_path), n_nodes=3)
    states = np.array([INFECTED, SUSCEPTIBLE, SUSCEPTIBLE], dtype=np.int8)

    first = sir_step(graph, states, 0.5, 0.25, np.random.default_rng(99), t=1.0)
    second = sir_step(graph, states, 0.5, 0.25, np.random.default_rng(99), t=1.0)

    np.testing.assert_array_equal(first.states, second.states)
    assert first.events == second.events
