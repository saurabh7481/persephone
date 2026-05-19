from __future__ import annotations

from collections.abc import Callable, Iterable
from importlib.metadata import entry_points
from typing import Protocol

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from persephone_sdk import __version__ as sdk_version
from persephone_sdk.plugin import PluginManifest


class PluginRegistryError(RuntimeError):
    """Base class for plugin registry failures."""


class PluginNotFoundError(PluginRegistryError):
    """Raised when a requested plugin is not installed."""


class PluginVersionError(PluginRegistryError):
    """Raised when an installed plugin does not satisfy a version constraint."""


class PluginLoadError(PluginRegistryError):
    """Raised when a plugin entry point cannot be loaded."""


class EntryPointLike(Protocol):
    name: str

    def load(self) -> object: ...


EntryPointsProvider = Callable[[], Iterable[EntryPointLike]]


def _default_entry_points_provider() -> Iterable[EntryPointLike]:
    return entry_points(group="persephone.plugins")


class PluginRegistry:
    def __init__(
        self,
        entry_points_provider: EntryPointsProvider = _default_entry_points_provider,
        installed_sdk_version: str = sdk_version,
    ) -> None:
        self._entry_points_provider = entry_points_provider
        self._installed_sdk_version = Version(installed_sdk_version)
        self._plugins: dict[str, PluginManifest] = {}
        self.load_errors: dict[str, str] = {}

    def discover(self) -> None:
        self._plugins.clear()
        self.load_errors.clear()

        for entry_point in self._entry_points_provider():
            try:
                plugin_class = entry_point.load()
                manifest = self._load_manifest(entry_point.name, plugin_class)
                self._validate_sdk_version(manifest)
            except Exception as exc:  # noqa: BLE001 - discovery must isolate broken plugins.
                self.load_errors[entry_point.name] = str(exc)
                continue

            self._plugins[entry_point.name] = manifest

    def get(self, name: str) -> PluginManifest:
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise PluginNotFoundError(
                f"Plugin '{name}' is not installed. Run: pip install persephone-plugin-{name}"
            ) from exc

    def require(self, name: str, version_constraint: str) -> PluginManifest:
        manifest = self.get(name)
        specifier = SpecifierSet(version_constraint)
        if Version(manifest.version) not in specifier:
            raise PluginVersionError(
                f"Plugin '{name}' version {manifest.version} does not satisfy {version_constraint}"
            )
        return manifest

    def list_all(self) -> list[dict[str, str]]:
        return [
            {"name": name, "version": manifest.version, "paradigm": manifest.paradigm}
            for name, manifest in sorted(self._plugins.items())
        ]

    def _load_manifest(self, entry_point_name: str, plugin_class: object) -> PluginManifest:
        manifest_factory = getattr(plugin_class, "manifest", None)
        if manifest_factory is None:
            raise PluginLoadError(f"Plugin '{entry_point_name}' has no manifest() method")

        manifest = manifest_factory()
        if not isinstance(manifest, PluginManifest):
            raise PluginLoadError(
                f"Plugin '{entry_point_name}' manifest() did not return PluginManifest"
            )
        return manifest

    def _validate_sdk_version(self, manifest: PluginManifest) -> None:
        required = Version(manifest.sdk_min_version)
        if self._installed_sdk_version < required:
            raise PluginVersionError(
                f"Plugin '{manifest.name}' requires persephone-sdk>={manifest.sdk_min_version}; "
                f"installed {self._installed_sdk_version}"
            )
