from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from time import perf_counter, sleep
from typing import Any, cast

import numpy as np
from numpy.random import Generator
from persephone_sdk.plugin import Observer, Renderer, Solver
from persephone_sdk.types import StateDict

from persephone.core.bus import BusCommitSummary, InMemoryDataBus
from persephone.core.explanations import summarize_explanation_packet, validate_explanation_packet
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


@dataclass(frozen=True)
class ObservationBatch:
    metrics: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


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
                observations = self._observe(t, tick=tick)
                self._emit_scheduler_telemetry(
                    tick=tick,
                    logical_time=t,
                    sync_interval_used=elapsed_interval,
                    tick_started=tick_started,
                    solver_step_times=solver_step_times,
                    commit_summary=commit_summary,
                )
                frames_by_solver = self._emit_frames(t, tick=tick)
                self._emit_explanations(
                    t,
                    tick=tick,
                    observations=observations,
                    frames_by_solver=frames_by_solver,
                )
                self._checkpoint_if_needed(tick=tick, logical_time=t)
                self._delay_demo_tick()

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

    def _observe(self, t: float, tick: int) -> dict[str, ObservationBatch]:
        batches = {runtime.solver_id: ObservationBatch() for runtime in self.runtimes}
        emit_every = self._emit_every()
        if t + 1e-9 < emit_every and t + 1e-9 < self._t_end():
            return batches
        if not _is_cadence_time(t, emit_every) and t + 1e-9 < self._t_end():
            return batches

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
            batches[runtime.solver_id] = ObservationBatch(
                metrics=metric_records,
                events=event_records,
            )
        return batches

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

    def _emit_frames(self, t: float, *, tick: int) -> dict[str, list[dict[str, Any]]]:
        frames_by_solver = {runtime.solver_id: [] for runtime in self.runtimes}
        emit_every = self._visualization_emit_every()
        if t + 1e-9 < emit_every:
            return frames_by_solver
        if not _is_cadence_time(t, emit_every):
            return frames_by_solver

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
                validated = validate_frame(cast(dict[str, Any], frame)).model_dump(mode="json")
                frames.append(validated)
                frames_by_solver[runtime.solver_id].append(validated)
        self.artifact_store.write_frames(self.run_context.run_id, frames)
        self._emit_records("frame", frames)
        return frames_by_solver

    def _emit_explanations(
        self,
        t: float,
        *,
        tick: int,
        observations: dict[str, ObservationBatch],
        frames_by_solver: dict[str, list[dict[str, Any]]],
    ) -> None:
        packets: list[dict[str, Any]] = []
        for runtime in self.runtimes:
            batch = observations.get(runtime.solver_id, ObservationBatch())
            raw_packets = runtime.observer.explain(
                runtime.state,
                t=t,
                tick=tick,
                run_id=self.run_context.run_id,
                solver_id=runtime.solver_id,
                metrics=cast(Any, batch.metrics),
                events=cast(Any, batch.events),
                frames=cast(Any, frames_by_solver.get(runtime.solver_id, [])),
            )
            for raw_packet in raw_packets:
                packet = validate_explanation_packet(
                    {
                        "run_id": self.run_context.run_id,
                        "solver_id": runtime.solver_id,
                        "t": t,
                        "tick": tick,
                        **raw_packet,
                    }
                )
                packet.summary = summarize_explanation_packet(packet)
                packets.append(packet.model_dump(mode="json"))
        self.artifact_store.write_explanations(self.run_context.run_id, packets)
        self._emit_records("explanation", packets)

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

    def _delay_demo_tick(self) -> None:
        scheduler = cast(Mapping[str, object], self.run_context.config_snapshot["scheduler"])
        delay_ms = int(cast(int, scheduler.get("demo_delay_ms_per_tick", 0)))
        if delay_ms > 0:
            sleep(delay_ms / 1000.0)

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


def _is_cadence_time(t: float, cadence: float) -> bool:
    ratio = t / cadence
    return bool(np.isclose(ratio, round(ratio), atol=1e-9))
