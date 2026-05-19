from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

CouplingRule = Literal["sum", "mean", "max", "min", "last"]


class BusError(RuntimeError):
    """Base class for data bus failures."""


class BusSchemaError(BusError):
    """Raised when a bus write violates a channel schema."""


class BusConflictError(BusError):
    """Raised when duplicate writes have no coupling rule."""


@dataclass(frozen=True)
class BusChannelSchema:
    name: str
    dtype: str
    shape: tuple[int, ...]
    units: str | None = None
    schema_id: str | None = None

    @property
    def numpy_dtype(self) -> np.dtype:
        return np.dtype(self.dtype)


@dataclass(frozen=True)
class BusRecord:
    run_id: str
    tick: int
    solver_id: str
    schema_id: str
    logical_time: float
    value: NDArray[np.generic]
    units: str | None = None


class InMemoryDataBus:
    def __init__(
        self,
        run_id: str,
        schemas: dict[str, BusChannelSchema],
        coupling_rules: dict[str, CouplingRule] | None = None,
    ) -> None:
        self.run_id = run_id
        self._schemas = schemas
        self._coupling_rules = coupling_rules or {}
        self._committed: dict[str, BusRecord] = {}
        self._pending: dict[str, list[BusRecord]] = {}

    def read(self, channel: str) -> NDArray[np.generic] | None:
        record = self._committed.get(channel)
        if record is None:
            return None
        return record.value.copy()

    def write(
        self,
        channel: str,
        value: NDArray[np.generic],
        solver_id: str,
        tick: int,
        logical_time: float | None = None,
    ) -> None:
        schema = self._schema_for(channel)
        array = np.asarray(value)
        self._validate_value(channel, array, schema)

        record = BusRecord(
            run_id=self.run_id,
            tick=tick,
            solver_id=solver_id,
            schema_id=schema.schema_id or channel,
            logical_time=float(tick if logical_time is None else logical_time),
            value=array.copy(),
            units=schema.units,
        )
        self._pending.setdefault(channel, []).append(record)

    def commit(self, tick: int) -> None:
        for channel, records in self._pending.items():
            if len(records) == 1:
                self._committed[channel] = records[0]
                continue

            rule = self._coupling_rules.get(channel)
            if rule is None:
                raise BusConflictError(
                    f"Channel '{channel}' received {len(records)} writes without a coupling rule"
                )
            self._committed[channel] = self._couple(channel, records, rule, tick)

        self._pending.clear()

    def _schema_for(self, channel: str) -> BusChannelSchema:
        try:
            return self._schemas[channel]
        except KeyError as exc:
            raise BusSchemaError(f"No schema declared for bus channel '{channel}'") from exc

    def _validate_value(
        self, channel: str, value: NDArray[np.generic], schema: BusChannelSchema
    ) -> None:
        if value.shape != schema.shape:
            raise BusSchemaError(
                f"Bus channel '{channel}' expected shape {schema.shape}, got {value.shape}"
            )
        if value.dtype != schema.numpy_dtype:
            raise BusSchemaError(
                f"Bus channel '{channel}' expected dtype {schema.numpy_dtype}, got {value.dtype}"
            )

    def _couple(
        self, channel: str, records: list[BusRecord], rule: CouplingRule, tick: int
    ) -> BusRecord:
        values = np.stack([record.value for record in records])
        match rule:
            case "sum":
                value = values.sum(axis=0)
            case "mean":
                value = values.mean(axis=0)
            case "max":
                value = values.max(axis=0)
            case "min":
                value = values.min(axis=0)
            case "last":
                value = records[-1].value

        schema = self._schema_for(channel)
        return BusRecord(
            run_id=self.run_id,
            tick=tick,
            solver_id="coupled",
            schema_id=schema.schema_id or channel,
            logical_time=float(tick),
            value=np.asarray(value, dtype=schema.numpy_dtype).copy(),
            units=schema.units,
        )
