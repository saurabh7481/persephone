from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from persephone_sdk.plugin import PluginManifest

from persephone.config.models import ExperimentConfig
from persephone.core.bus import BusChannelSchema, InMemoryDataBus
from persephone.core.run import RunContext
from persephone.core.scheduler import Scheduler, SolverRuntime
from persephone.registry.registry import PluginRegistry
from persephone.storage.artifacts import ArtifactStore


@dataclass(frozen=True)
class RunResult:
    run_id: str
    status: str
    artifact_path: Path
    final_time: float
    metric_summary: dict[str, float]
    error_message: str | None = None


class PersephoneEngine:
    def __init__(
        self,
        registry: PluginRegistry | None = None,
        artifact_root: str | Path = "runs",
    ) -> None:
        self.registry = registry or PluginRegistry()
        self.artifact_root = Path(artifact_root)

    def validate(self, config: ExperimentConfig) -> dict[str, PluginManifest]:
        self.registry.discover()
        manifests: dict[str, PluginManifest] = {}
        active_writes: set[str] = set()

        for solver_config in config.solvers:
            manifest = self.registry.require(solver_config.plugin, solver_config.version)
            manifests[solver_config.plugin] = manifest
            active_writes.update(manifest.bus_writes)

        missing_reads = sorted(
            {
                channel
                for manifest in manifests.values()
                for channel in manifest.bus_reads
                if channel not in active_writes
            }
        )
        if missing_reads:
            raise ValueError(f"Bus channel reads have no active writer: {', '.join(missing_reads)}")

        return manifests

    def run(self, config: ExperimentConfig, run_id: str | None = None) -> RunResult:
        manifests = self.validate(config)
        run_context = RunContext.create(config, manifests, run_id=run_id)
        artifact_store = ArtifactStore(self.artifact_root)
        artifact_path = artifact_store.initialize_run(run_context)
        runtimes, schemas = self._build_runtimes(config, manifests, run_context)
        bus = InMemoryDataBus(
            run_id=run_context.run_id,
            schemas=schemas,
            coupling_rules=config.coupling.rules,
        )
        scheduler = Scheduler(
            run_context=run_context,
            runtimes=runtimes,
            bus=bus,
            artifact_store=artifact_store,
        )

        scheduler_result = scheduler.run()
        return RunResult(
            run_id=run_context.run_id,
            status=scheduler_result.status,
            artifact_path=artifact_path,
            final_time=scheduler_result.t_current,
            metric_summary=self._metric_summary(runtimes),
            error_message=scheduler_result.error_message,
        )

    def _build_runtimes(
        self,
        config: ExperimentConfig,
        manifests: dict[str, PluginManifest],
        run_context: RunContext,
    ) -> tuple[list[SolverRuntime], dict[str, BusChannelSchema]]:
        runtimes: list[SolverRuntime] = []
        schemas: dict[str, BusChannelSchema] = {}

        for index, solver_config in enumerate(config.solvers):
            manifest = manifests[solver_config.plugin]
            world = manifest.world()
            solver_id = f"{manifest.name}#{index}"
            state = world.init(solver_config.params, seed=run_context.seed_plan[solver_id])
            solver = manifest.solver()
            observer = manifest.observer()
            runtimes.append(
                SolverRuntime(
                    solver_id=solver_id,
                    solver=solver,
                    observer=observer,
                    state=state,
                    rng=np.random.default_rng(run_context.seed_plan[solver_id]),
                )
            )
            schemas.update(self._schemas_for_manifest(manifest, state))

        return runtimes, schemas

    def _schemas_for_manifest(
        self, manifest: PluginManifest, state: dict[str, np.ndarray]
    ) -> dict[str, BusChannelSchema]:
        schemas: dict[str, BusChannelSchema] = {}
        for channel in manifest.bus_writes:
            if channel not in state:
                continue
            value = state[channel]
            schemas[channel] = BusChannelSchema(
                name=channel,
                dtype=str(value.dtype),
                shape=value.shape,
            )
        return schemas

    def _metric_summary(self, runtimes: list[SolverRuntime]) -> dict[str, float]:
        summary: dict[str, float] = {}
        for runtime in runtimes:
            metrics = runtime.observer.observe(runtime.state, t=0.0, run_id="")
            for metric in metrics:
                value = metric.get("value")
                if isinstance(value, int | float):
                    summary[str(metric["metric"])] = float(value)
        return summary
