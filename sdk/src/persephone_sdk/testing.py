from __future__ import annotations

from typing import Any

import numpy as np

from persephone_sdk.plugin import PluginManifest, is_finite_state


class SpyDataBus:
    def __init__(self) -> None:
        self.written_channels: list[str] = []
        self.read_channels: list[str] = []
        self.records: list[dict[str, Any]] = []

    def write(self, channel: str, value: Any, solver_id: str, tick: int) -> None:
        self.written_channels.append(channel)
        self.records.append(
            {"channel": channel, "value": value, "solver_id": solver_id, "tick": tick}
        )

    def read(self, channel: str) -> None:
        self.read_channels.append(channel)
        return None


class PluginTestHarness:
    """Standard compliance suite for Persephone plugins."""

    def __init__(self, plugin_class: type[Any]) -> None:
        self.plugin_class = plugin_class
        manifest = plugin_class.manifest()
        if not isinstance(manifest, PluginManifest):
            raise TypeError("plugin manifest() must return PluginManifest")
        self.manifest = manifest

    def run_all(self) -> None:
        self.test_schema_matches_init_output()
        self.test_solver_step_is_finite()
        self.test_reset_returns_identical_state()
        self.test_bus_writes_match_declared_channels()
        self.test_bus_reads_match_declared_channels()
        self.test_observer_and_renderer_contracts()
        self.test_manifest_sdk_version_present()

    def test_schema_matches_init_output(self) -> None:
        world = self.manifest.world()
        state = world.init(self.manifest.default_params, seed=42)
        schema = world.schema()
        for key, shape in schema.items():
            assert key in state, f"Key '{key}' declared in schema but missing from init()"
            assert state[key].shape == shape, f"Shape mismatch for '{key}'"

    def test_solver_step_is_finite(self) -> None:
        world = self.manifest.world()
        state = world.init(self.manifest.default_params, seed=42)
        bus = SpyDataBus()
        solver = self.manifest.solver()
        new_state, dt_advanced = solver.step(state, dt=solver.preferred_dt, bus=bus)
        assert dt_advanced > 0, "Solver must report positive elapsed time"
        assert is_finite_state(new_state), "Solver returned non-finite state values"

    def test_reset_returns_identical_state(self) -> None:
        world = self.manifest.world()
        initial = world.init(self.manifest.default_params, seed=42)
        reset = world.reset()
        for key, initial_value in initial.items():
            np.testing.assert_array_equal(initial_value, reset[key])

    def test_bus_writes_match_declared_channels(self) -> None:
        world = self.manifest.world()
        state = world.init(self.manifest.default_params, seed=42)
        bus = SpyDataBus()
        solver = self.manifest.solver()
        solver.step(state, dt=solver.preferred_dt, bus=bus)
        for channel in bus.written_channels:
            assert channel in self.manifest.bus_writes, (
                f"Plugin wrote to undeclared bus channel '{channel}'"
            )

    def test_bus_reads_match_declared_channels(self) -> None:
        world = self.manifest.world()
        state = world.init(self.manifest.default_params, seed=42)
        bus = SpyDataBus()
        solver = self.manifest.solver()
        solver.step(state, dt=solver.preferred_dt, bus=bus)
        for channel in bus.read_channels:
            assert channel in self.manifest.bus_reads, (
                f"Plugin read from undeclared bus channel '{channel}'"
            )

    def test_observer_and_renderer_contracts(self) -> None:
        world = self.manifest.world()
        state = world.init(self.manifest.default_params, seed=42)
        observer = self.manifest.observer()
        renderer = self.manifest.renderer()

        metrics = observer.observe(state, t=0.0, run_id="harness")
        assert isinstance(metrics, list), "Observer must return a list"
        assert isinstance(renderer.viz_schema(), dict), "Renderer must return a dict"

    def test_manifest_sdk_version_present(self) -> None:
        assert self.manifest.sdk_min_version, "sdk_min_version must be set"
