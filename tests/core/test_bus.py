from __future__ import annotations

import numpy as np
import pytest

from persephone.core.bus import BusChannelSchema, BusConflictError, BusSchemaError, InMemoryDataBus


def test_current_tick_writes_are_invisible_until_commit() -> None:
    bus = InMemoryDataBus(
        run_id="run-1",
        schemas={"temperature": BusChannelSchema(name="temperature", dtype="float64", shape=(2,))},
    )

    bus.write("temperature", np.array([1.0, 2.0]), solver_id="solver-a", tick=1)

    assert bus.read("temperature") is None
    bus.commit(tick=1)
    np.testing.assert_array_equal(bus.read("temperature"), np.array([1.0, 2.0]))


@pytest.mark.parametrize(
    ("rule", "expected"),
    [
        ("sum", np.array([4.0, 6.0])),
        ("mean", np.array([2.0, 3.0])),
        ("max", np.array([3.0, 4.0])),
        ("min", np.array([1.0, 2.0])),
        ("last", np.array([3.0, 4.0])),
    ],
)
def test_coupling_rules_resolve_duplicate_writes(rule: str, expected: np.ndarray) -> None:
    bus = InMemoryDataBus(
        run_id="run-1",
        schemas={"x": BusChannelSchema(name="x", dtype="float64", shape=(2,))},
        coupling_rules={"x": rule},
    )

    bus.write("x", np.array([1.0, 2.0]), solver_id="a", tick=1)
    bus.write("x", np.array([3.0, 4.0]), solver_id="b", tick=1)
    bus.commit(tick=1)

    np.testing.assert_array_equal(bus.read("x"), expected)


def test_duplicate_writes_without_coupling_rule_are_rejected() -> None:
    bus = InMemoryDataBus(
        run_id="run-1",
        schemas={"x": BusChannelSchema(name="x", dtype="float64", shape=(1,))},
    )

    bus.write("x", np.array([1.0]), solver_id="a", tick=1)
    bus.write("x", np.array([2.0]), solver_id="b", tick=1)

    with pytest.raises(BusConflictError, match="x"):
        bus.commit(tick=1)


def test_schema_violations_are_rejected_on_write() -> None:
    bus = InMemoryDataBus(
        run_id="run-1",
        schemas={"x": BusChannelSchema(name="x", dtype="float64", shape=(2,))},
    )

    with pytest.raises(BusSchemaError, match="shape"):
        bus.write("x", np.array([1.0]), solver_id="a", tick=1)

    with pytest.raises(BusSchemaError, match="dtype"):
        bus.write("x", np.array([1, 2], dtype=np.int64), solver_id="a", tick=1)
