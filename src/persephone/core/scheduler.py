from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.random import Generator
from persephone_sdk.plugin import Observer, Solver
from persephone_sdk.types import StateDict

from persephone.core.bus import InMemoryDataBus
from persephone.core.run import RunContext
from persephone.storage.artifacts import ArtifactStore


@dataclass
class SolverRuntime:
    solver_id: str
    solver: Solver
    observer: Observer
    state: StateDict
    rng: Generator


@dataclass(frozen=True)
class SchedulerResult:
    status: str
    tick_count: int
    t_current: float
    error_message: str | None = None


class Scheduler:
    def __init__(
        self,
        run_context: RunContext,
        runtimes: list[SolverRuntime],
        bus: InMemoryDataBus,
        artifact_store: ArtifactStore,
    ) -> None:
        self.run_context = run_context
        self.runtimes = runtimes
        self.bus = bus
        self.artifact_store = artifact_store

    def run(self) -> SchedulerResult:
        t = 0.0
        tick = 0
        self.artifact_store.update_status(self.run_context.run_id, "running", t_current=t)

        try:
            while t < self._t_end():
                tick += 1
                dt = self._next_dt(t)
                for runtime in self.runtimes:
                    self._attach_rng(runtime)
                    new_state, elapsed = runtime.solver.step(runtime.state, dt, self.bus)
                    if elapsed <= 0:
                        raise RuntimeError("Solver must report positive elapsed time")
                    runtime.state = new_state

                t += dt
                self.bus.commit(tick=tick)
                self._observe(t)

            self.artifact_store.write_final_state(self.run_context.run_id, self._final_state())
            self.artifact_store.update_status(self.run_context.run_id, "completed", t_current=t)
            return SchedulerResult(status="completed", tick_count=tick, t_current=t)
        except Exception as exc:  # noqa: BLE001 - scheduler records failure boundary.
            self.artifact_store.update_status(
                self.run_context.run_id,
                "failed",
                t_current=t,
                error_message=str(exc),
            )
            return SchedulerResult(
                status="failed",
                tick_count=tick,
                t_current=t,
                error_message=str(exc),
            )

    def _next_dt(self, t: float) -> float:
        t_end = self._t_end()
        preferred = min(runtime.solver.preferred_dt for runtime in self.runtimes)
        return min(preferred, t_end - t)

    def _attach_rng(self, runtime: SolverRuntime) -> None:
        solver = cast(Any, runtime.solver)
        solver.rng = runtime.rng

    def _t_end(self) -> float:
        scheduler = cast(Mapping[str, object], self.run_context.config_snapshot["scheduler"])
        return float(cast(int | float | str, scheduler["t_end"]))

    def _observe(self, t: float) -> None:
        for runtime in self.runtimes:
            metrics = runtime.observer.observe(runtime.state, t=t, run_id=self.run_context.run_id)
            for metric in metrics:
                metric.setdefault("solver_id", runtime.solver_id)
            self.artifact_store.write_metrics(self.run_context.run_id, metrics)

            events = getattr(runtime.solver, "last_events", [])
            for event in events:
                event.setdefault("solver_id", runtime.solver_id)
            self.artifact_store.write_events(self.run_context.run_id, list(events))

    def _final_state(self) -> dict[str, np.ndarray[Any, Any]]:
        state: dict[str, np.ndarray[Any, Any]] = {}
        for runtime in self.runtimes:
            for key, value in runtime.state.items():
                state[f"{runtime.solver_id}.{key}"] = value
        return state
