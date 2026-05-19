# Plugin Authoring

Persephone plugins are Python packages that depend on `persephone-sdk` and register themselves through the `persephone.plugins` entry point group.

## Required Interfaces

Every plugin exposes a `PluginManifest` and implements four SDK interfaces:

- `World`: defines state shape, initializes state, and resets state.
- `Solver`: advances state by one time interval.
- `Observer`: emits metrics from committed state.
- `Renderer`: returns visualization hints for UI consumers.

## Minimal Package Layout

```text
persephone-plugin-example/
├── pyproject.toml
└── src/persephone_example/
    ├── __init__.py
    ├── world.py
    ├── solver.py
    ├── observer.py
    └── renderer.py
```

## Entry Point

```toml
[project.entry-points."persephone.plugins"]
example = "persephone_example:ExamplePlugin"
```

The entry-point name is what experiment configs use in `solvers[].plugin`.

## Manifest

```python
from persephone_sdk.plugin import PluginManifest

class ExamplePlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="example",
            version="0.1.0",
            paradigm="graph",
            world=ExampleWorld,
            solver=ExampleSolver,
            observer=ExampleObserver,
            renderer=ExampleRenderer,
            bus_reads=[],
            bus_writes=["states"],
            default_params={},
            params_schema={},
            metrics_schema={},
            sdk_min_version="0.1.0",
        )
```

## Testing

Use the SDK harness in the plugin test suite:

```python
from persephone_sdk.testing import PluginTestHarness
from persephone_example import ExamplePlugin

def test_plugin_contracts():
    PluginTestHarness(ExamplePlugin).run_all()
```

For scientific plugins, add domain tests too. The SIR plugin tests population conservation and deterministic outcomes for the same seed.

## Trust Model

Version 1 plugins are trusted Python packages. There is no sandbox. Do not install plugins from untrusted sources.

