from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from persephone.core.coupling import coupling_registry

CouplingRule = str


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
    value_kind: str = "ndarray"
    schema_version: int = 1

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


@dataclass(frozen=True)
class BusCommitSummary:
    conflicts: dict[str, int]
    coupling_rules: dict[str, str]


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
        invalid_rules = {
            channel: rule
            for channel, rule in self._coupling_rules.items()
            if not coupling_registry.has(rule)
        }
        if invalid_rules:
            channel, rule = next(iter(invalid_rules.items()))
            raise BusSchemaError(f"Invalid coupling rule '{rule}' for channel '{channel}'")
        self._committed: dict[str, BusRecord] = {}
        self._pending: dict[str, list[BusRecord]] = {}
        self.last_commit_summary = BusCommitSummary(conflicts={}, coupling_rules={})

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

    def commit(self, tick: int, logical_time: float | None = None) -> BusCommitSummary:
        conflicts: dict[str, int] = {}
        coupling_rules: dict[str, str] = {}
        for channel, records in self._pending.items():
            if len(records) == 1:
                self._committed[channel] = records[0]
                continue

            rule = self._coupling_rules.get(channel)
            if rule is None:
                raise BusConflictError(
                    f"Channel '{channel}' received {len(records)} writes without a coupling rule"
                )
            conflicts[channel] = len(records)
            coupling_rules[channel] = rule
            self._committed[channel] = self._couple(channel, records, rule, tick, logical_time)

        self._pending.clear()
        self.last_commit_summary = BusCommitSummary(
            conflicts=conflicts,
            coupling_rules=coupling_rules,
        )
        return self.last_commit_summary

    def channel_sizes(self) -> dict[str, int]:
        return {channel: int(record.value.nbytes) for channel, record in self._committed.items()}

    def snapshot(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "schemas": {
                channel: {
                    "name": schema.name,
                    "dtype": schema.dtype,
                    "shape": list(schema.shape),
                    "units": schema.units,
                    "schema_id": schema.schema_id,
                    "value_kind": schema.value_kind,
                    "schema_version": schema.schema_version,
                }
                for channel, schema in self._schemas.items()
            },
            "coupling_rules": dict(self._coupling_rules),
            "committed": {
                channel: {
                    "run_id": record.run_id,
                    "tick": record.tick,
                    "solver_id": record.solver_id,
                    "schema_id": record.schema_id,
                    "logical_time": record.logical_time,
                    "value": record.value.tolist(),
                    "units": record.units,
                }
                for channel, record in self._committed.items()
            },
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> InMemoryDataBus:
        schemas = {
            channel: BusChannelSchema(
                name=str(data["name"]),
                dtype=str(data["dtype"]),
                shape=tuple(cast(list[int], data["shape"])),
                units=cast(str | None, data.get("units")),
                schema_id=cast(str | None, data.get("schema_id")),
                value_kind=str(data.get("value_kind", "ndarray")),
                schema_version=int(data.get("schema_version", 1)),
            )
            for channel, data in cast(dict[str, dict[str, Any]], snapshot["schemas"]).items()
        }
        bus = cls(
            run_id=str(snapshot["run_id"]),
            schemas=schemas,
            coupling_rules=cast(dict[str, CouplingRule], snapshot.get("coupling_rules", {})),
        )
        for channel, data in cast(dict[str, dict[str, Any]], snapshot.get("committed", {})).items():
            schema = schemas[channel]
            bus._committed[channel] = BusRecord(
                run_id=str(data["run_id"]),
                tick=int(data["tick"]),
                solver_id=str(data["solver_id"]),
                schema_id=str(data["schema_id"]),
                logical_time=float(data["logical_time"]),
                value=np.asarray(data["value"], dtype=schema.numpy_dtype),
                units=cast(str | None, data.get("units")),
            )
        return bus

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
        self,
        channel: str,
        records: list[BusRecord],
        rule: CouplingRule,
        tick: int,
        logical_time: float | None,
    ) -> BusRecord:
        values = np.stack([record.value for record in records])
        value = coupling_registry.resolve(rule)(values)

        schema = self._schema_for(channel)
        return BusRecord(
            run_id=self.run_id,
            tick=tick,
            solver_id="coupled",
            schema_id=schema.schema_id or channel,
            logical_time=float(tick if logical_time is None else logical_time),
            value=np.asarray(value, dtype=schema.numpy_dtype).copy(),
            units=schema.units,
        )
