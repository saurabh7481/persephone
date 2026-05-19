from __future__ import annotations

from typing import Any

import pytest
from persephone_sdk.plugin import Observer, PluginManifest, Renderer, Solver, World

from persephone.registry.registry import (
    PluginNotFoundError,
    PluginRegistry,
    PluginVersionError,
)


class RegistryWorld(World):
    def schema(self) -> dict[str, tuple[int, ...]]:
        return {"x": (1,)}

    def init(self, params: dict[str, Any], seed: int) -> dict[str, Any]:
        return {"x": params.get("x")}

    def reset(self) -> dict[str, Any]:
        return {"x": 0}


class RegistrySolver(Solver):
    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(self, state: dict[str, Any], dt: float, bus: Any) -> tuple[dict[str, Any], float]:
        return state, dt


class RegistryObserver(Observer):
    def observe(self, state: dict[str, Any], t: float, run_id: str) -> list[dict[str, Any]]:
        return []


class RegistryRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {"type": "none"}


def manifest(
    name: str = "demo",
    version: str = "0.2.0",
    sdk_min_version: str = "0.1.0",
) -> PluginManifest:
    return PluginManifest(
        name=name,
        version=version,
        paradigm="graph",
        world=RegistryWorld,
        solver=RegistrySolver,
        observer=RegistryObserver,
        renderer=RegistryRenderer,
        bus_reads=[],
        bus_writes=[],
        default_params={},
        params_schema={},
        metrics_schema={},
        sdk_min_version=sdk_min_version,
    )


class FakePlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return manifest()


class FakeEntryPoint:
    def __init__(self, name: str, plugin: type[Any] | Exception) -> None:
        self.name = name
        self._plugin = plugin

    def load(self) -> type[Any]:
        if isinstance(self._plugin, Exception):
            raise self._plugin
        return self._plugin


def test_registry_discovers_plugin_manifests_from_entry_points() -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [FakeEntryPoint("demo", FakePlugin)])

    registry.discover()

    assert registry.get("demo").name == "demo"
    assert registry.list_all() == [{"name": "demo", "version": "0.2.0", "paradigm": "graph"}]


def test_registry_skips_broken_entry_points_without_crashing() -> None:
    registry = PluginRegistry(
        entry_points_provider=lambda: [
            FakeEntryPoint("broken", RuntimeError("boom")),
            FakeEntryPoint("demo", FakePlugin),
        ]
    )

    registry.discover()

    assert registry.get("demo").version == "0.2.0"
    assert "broken" in registry.load_errors


def test_registry_rejects_missing_plugins_and_incompatible_versions() -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [FakeEntryPoint("demo", FakePlugin)])
    registry.discover()

    with pytest.raises(PluginNotFoundError, match="missing"):
        registry.get("missing")

    with pytest.raises(PluginVersionError, match=">=1.0"):
        registry.require("demo", ">=1.0")


def test_registry_rejects_plugins_requiring_newer_sdk() -> None:
    class NewSdkPlugin:
        @staticmethod
        def manifest() -> PluginManifest:
            return manifest(sdk_min_version="99.0.0")

    registry = PluginRegistry(
        entry_points_provider=lambda: [FakeEntryPoint("future", NewSdkPlugin)]
    )

    registry.discover()

    assert "future" in registry.load_errors
    with pytest.raises(PluginNotFoundError):
        registry.get("future")
