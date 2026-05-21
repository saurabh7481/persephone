from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

import numpy as np
from numpy.random import Generator
from persephone_sdk.plugin import Observer, Renderer, Solver
from persephone_sdk.types import StateDict

from persephone.core.bus import BusCommitSummary, InMemoryDataBus
from persephone.core.frames import validate_frame
from persephone.core.records import SchedulerTelemetry
from persephone.core.run import RunContext
from persephone.storage.artifacts import ArtifactStore


@dataclass
class SolverRuntime:
    solver_id: str
    solver: Solver
    observer: Observer
    renderer: Renderer
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
        record_callback: Callable[[str, dict[str, Any]], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        self.run_context = run_context
        self.runtimes = runtimes
        self.bus = bus
        self.artifact_store = artifact_store
        self.record_callback = record_callback
        self.should_cancel = should_cancel

    def run(self) -> SchedulerResult:
        t = 0.0
        tick = 0
        self.artifact_store.update_status(self.run_context.run_id, "running", t_current=t)

        try:
            while t < self._t_end():
                if self.should_cancel is not None and self.should_cancel():
                    self.artifact_store.update_status(
                        self.run_context.run_id,
                        "cancelled",
                        t_current=t,
                    )
                    return SchedulerResult(status="cancelled", tick_count=tick, t_current=t)
                tick += 1
                dt = self._next_dt(t)
                tick_started = perf_counter()
                solver_step_times: dict[str, float] = {}
                elapsed_values: list[float] = []
                for runtime in self.runtimes:
                    self._attach_rng(runtime)
                    solver_started = perf_counter()
                    new_state, elapsed = runtime.solver.step(runtime.state, dt, self.bus)
                    solver_step_times[runtime.solver_id] = (
                        perf_counter() - solver_started
                    ) * 1000.0
                    if elapsed <= 0:
                        raise RuntimeError("Solver must report positive elapsed time")
                    if elapsed - dt > 1e-9:
                        raise RuntimeError(
                            "Solver advanced beyond requested interval: "
                            f"requested {dt}, got {elapsed}"
                        )
                    elapsed_values.append(float(elapsed))
                    runtime.state = new_state

                elapsed_interval = self._validated_elapsed_interval(dt, elapsed_values)
                t += elapsed_interval
                commit_summary = self.bus.commit(tick=tick, logical_time=t)
                self._observe(t, tick=tick)
                self._emit_scheduler_telemetry(
                    tick=tick,
                    logical_time=t,
                    sync_interval_used=elapsed_interval,
                    tick_started=tick_started,
                    solver_step_times=solver_step_times,
                    commit_summary=commit_summary,
                )
                self._emit_frames(t, tick=tick)
                self._checkpoint_if_needed(tick=tick, logical_time=t)

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
            self._emit_failure_telemetry(tick=tick, logical_time=t, error_message=str(exc))
            return SchedulerResult(
                status="failed",
                tick_count=tick,
                t_current=t,
                error_message=str(exc),
            )

    def _next_dt(self, t: float) -> float:
        t_end = self._t_end()
        preferred = min(runtime.solver.preferred_dt for runtime in self.runtimes)
        scheduler = cast(Mapping[str, object], self.run_context.config_snapshot["scheduler"])
        sync_interval = scheduler.get("sync_interval", "auto")
        configured_dt = scheduler.get("dt")
        window = preferred if sync_interval == "auto" else float(cast(float, sync_interval))
        if configured_dt is not None:
            window = min(window, float(cast(float, configured_dt)))
        return min(preferred, window, t_end - t)

    def _attach_rng(self, runtime: SolverRuntime) -> None:
        solver = cast(Any, runtime.solver)
        solver.rng = runtime.rng

    def _t_end(self) -> float:
        scheduler = cast(Mapping[str, object], self.run_context.config_snapshot["scheduler"])
        return float(cast(int | float | str, scheduler["t_end"]))

    def _observe(self, t: float, tick: int) -> None:
        emit_every = self._emit_every()
        if t + 1e-9 < emit_every and t + 1e-9 < self._t_end():
            return
        if not np.isclose((t / emit_every) % 1.0, 0.0, atol=1e-9) and t + 1e-9 < self._t_end():
            return

        for runtime in self.runtimes:
            metrics = runtime.observer.observe(runtime.state, t=t, run_id=self.run_context.run_id)
            for metric in metrics:
                metric.setdefault("solver_id", runtime.solver_id)
                metric.setdefault("run_id", self.run_context.run_id)
                metric.setdefault("tags", {})
            metric_records = cast(list[dict[str, Any]], metrics)
            self.artifact_store.write_metrics(self.run_context.run_id, metric_records)
            self._emit_records("metric", metric_records)

            events = cast(list[dict[str, Any]], getattr(runtime.solver, "last_events", []))
            for event in events:
                event.setdefault("solver_id", runtime.solver_id)
                event.setdefault("run_id", self.run_context.run_id)
                event.setdefault("t", t)
                event.setdefault("event", event.get("event_type", "event"))
                event.setdefault("tags", {})
            event_records = list(events)
            self.artifact_store.write_events(self.run_context.run_id, event_records)
            self._emit_records("event", event_records)

    def _emit_scheduler_telemetry(
        self,
        *,
        tick: int,
        logical_time: float,
        sync_interval_used: float,
        tick_started: float,
        solver_step_times: dict[str, float],
        commit_summary: BusCommitSummary,
    ) -> None:
        telemetry = SchedulerTelemetry(
            tick=tick,
            logical_time=logical_time,
            wall_time_ms=(perf_counter() - tick_started) * 1000.0,
            sync_interval_used=sync_interval_used,
            solver_step_times=solver_step_times,
            cfl_constrained=sync_interval_used < self._requested_window(logical_time),
            coupling_conflicts=commit_summary.conflicts,
            coupling_rules=commit_summary.coupling_rules,
            bus_channel_sizes=self.bus.channel_sizes(),
        )
        records = telemetry.to_metric_records(self.run_context.run_id)
        self.artifact_store.write_metrics(self.run_context.run_id, records)
        self._emit_records("metric", records)

    def _emit_failure_telemetry(
        self,
        *,
        tick: int,
        logical_time: float,
        error_message: str,
    ) -> None:
        record = {
            "run_id": self.run_context.run_id,
            "solver_id": "scheduler",
            "metric": "scheduler.failure",
            "value": 1.0,
            "t": logical_time,
            "tags": {"tick": str(tick), "error": error_message},
        }
        try:
            self.artifact_store.write_metrics(self.run_context.run_id, [record])
            self._emit_records("metric", [record])
        except Exception:
            pass

    def _emit_frames(self, t: float, *, tick: int) -> None:
        emit_every = self._visualization_emit_every()
        if t + 1e-9 < emit_every:
            return
        if not np.isclose((t / emit_every) % 1.0, 0.0, atol=1e-9):
            return

        frames: list[dict[str, Any]] = []
        for runtime in self.runtimes:
            raw_frames = runtime.renderer.frame(
                runtime.state,
                t=t,
                run_id=self.run_context.run_id,
                solver_id=runtime.solver_id,
                tick=tick,
                source="live",
            )
            for frame in raw_frames:
                frames.append(validate_frame(cast(dict[str, Any], frame)).model_dump(mode="json"))
        self._emit_records("frame", frames)

    def _checkpoint_if_needed(self, *, tick: int, logical_time: float) -> None:
        checkpoint_every = self._checkpoint_every()
        if checkpoint_every is None or tick % checkpoint_every != 0:
            return
        self.artifact_store.write_checkpoint(
            self.run_context.run_id,
            tick=tick,
            logical_time=logical_time,
            state=self._final_state(),
            bus_snapshot=self.bus.snapshot(),
            rng_states={
                runtime.solver_id: cast(dict[str, Any], runtime.rng.bit_generator.state)
                for runtime in self.runtimes
            },
        )

    def _emit_records(self, kind: str, records: list[dict[str, Any]]) -> None:
        if self.record_callback is None:
            return
        for record in records:
            self.record_callback(kind, record)

    def _final_state(self) -> dict[str, np.ndarray[Any, Any]]:
        state: dict[str, np.ndarray[Any, Any]] = {}
        for runtime in self.runtimes:
            for key, value in runtime.state.items():
                state[f"{runtime.solver_id}.{key}"] = cast(np.ndarray[Any, Any], value)
        return state

    def _emit_every(self) -> float:
        observer = cast(Mapping[str, object], self.run_context.config_snapshot.get("observer", {}))
        return float(cast(int | float, observer.get("emit_every", 1.0)))

    def _checkpoint_every(self) -> int | None:
        scheduler = cast(Mapping[str, object], self.run_context.config_snapshot["scheduler"])
        value = scheduler.get("checkpoint_every")
        return int(cast(int, value)) if value is not None else None

    def _visualization_emit_every(self) -> float:
        visualization = cast(
            Mapping[str, object], self.run_context.config_snapshot.get("visualization", {})
        )
        return float(cast(int | float, visualization.get("emit_every", 1.0)))

    def _validated_elapsed_interval(
        self,
        requested_dt: float,
        elapsed_values: list[float],
    ) -> float:
        if not elapsed_values:
            return requested_dt
        reference = elapsed_values[0]
        for elapsed in elapsed_values:
            if not np.isclose(elapsed, reference, atol=1e-9):
                raise RuntimeError("All solvers must advance the same elapsed interval per tick")
        if not np.isclose(reference, requested_dt, atol=1e-9):
            raise RuntimeError(
                "Solver elapsed time must match requested interval: "
                f"requested {requested_dt}, got {reference}"
            )
        return reference

    def _requested_window(self, logical_time: float) -> float:
        return self._next_dt(max(0.0, logical_time - 1e-9))
