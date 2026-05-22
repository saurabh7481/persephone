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

## Version 4 Semantic Manifest

Plugins can now declare a semantic contract through `PluginManifest.semantics`. This keeps the core platform domain-agnostic while letting the shared Studio use human-readable labels and better defaults.

```python
from persephone_sdk.plugin import (
    EntityField,
    ExplanationCapability,
    MetricDefinition,
    SemanticManifest,
    StateDefinition,
    ViewCapability,
)

SemanticManifest(
    entity_schemas={
        "service": [
            EntityField(name="label", type="string", label="Service", required=True),
            EntityField(name="owner", type="string", label="Owner"),
        ]
    },
    state_schema={
        "blocked": StateDefinition(name="blocked", kind="categorical", label="Blocked"),
    },
    metric_schema={
        "delivery_risk_index": MetricDefinition(
            name="delivery_risk_index",
            label="Delivery risk index",
            headline=True,
        )
    },
    view_capabilities=[
        ViewCapability(kind="hierarchy", label="Dependency hierarchy", default=True),
        ViewCapability(kind="table", label="Service table"),
    ],
    explanation_capabilities=[
        ExplanationCapability(scope="run", label="Run summary"),
        ExplanationCapability(scope="selection", label="Entity summary"),
    ],
    default_entity_type="service",
    preferred_view="hierarchy",
)
```

### Required vs optional fields

- `EntityField.name` and `EntityField.type` are required. Labels, descriptions, units, and `required=True` are optional but strongly recommended for inspector readability.
- `StateDefinition.name` and `StateDefinition.kind` are required. Use names that match the exact values you emit on nodes or entities.
- `MetricDefinition.name` is required. Mark only a small number of metrics as `headline=True` so the key-metric deck stays focused.
- `ViewCapability.kind` is required. Set `default=True` on the best reusable standard view, and also set `preferred_view` on the manifest when you want the run page to open there.
- `ExplanationCapability.scope` is required. Use `run`, `frame`, and `selection` only for scopes your plugin actually emits.
- Every top-level field on `SemanticManifest` is optional so v3 plugins continue to run, but new v4 plugins should fill in as much of the contract as they can.

## Explanation Hooks

`Observer.explain(...)` lets a plugin emit deterministic, evidence-backed fact packets. The engine stores these alongside run artifacts, and the UI can optionally paraphrase them later.

```python
def explain(self, state, *, t, tick, run_id, solver_id, metrics, events, frames):
    return [
        {
            "scope": "run",
            "facts": [
                {
                    "kind": "trend",
                    "title": "Delivery risk is clustering",
                    "summary": "Two services are driving most of the blocker pressure.",
                    "severity": "warning",
                    "evidence": [{"label": "delivery_risk_index", "value": 58}],
                    "related_ids": ["rules", "pricing"],
                    "t": t,
                }
            ],
        }
    ]
```

### Low-token interpretation guidance

- Prefer `interpretation.mode: rules_only` unless a concise paraphrase adds clear value.
- Emit compact evidence: metric names, values, units, and a few related ids. Do not send raw tensors or full event logs.
- Keep each fact focused on one claim. Multiple small facts are easier to cache and paraphrase than one giant paragraph.
- If you enable `minimal_ai`, bound the cost with `max_input_facts`, `max_output_tokens`, and milestone-triggered execution.
- Make every AI-facing summary traceable to deterministic `facts` and `evidence`.

## Choosing Default Views And Labels

- Use `preferred_view="heatmap"` for fixed-grid fields, `preferred_view="matrix"` for dense graphs, and `preferred_view="hierarchy"` or `table` when grouped entity inspection matters more than node-link playback.
- Always emit `label` on graph nodes or entity rows when the raw id is not already human-readable.
- Use `group` for reusable grouping, not one-off presentation hacks. The shared entity browser uses it to build hierarchy/table sections.
- Put rich human-facing details in `attrs` and reflect the most important ones in `entity_schemas` so the inspector can render them consistently.

## Migrating An Existing v3 Plugin

1. Keep the existing `World`, `Solver`, `Observer`, and `Renderer` behavior unchanged.
2. Add a `semantics=SemanticManifest(...)` block to `PluginManifest`.
3. Start small: entity labels, 1-2 headline metrics, and a preferred standard view.
4. Add `Observer.explain(...)` with deterministic run or selection facts if your domain already has clear milestone logic.
5. Run `PluginTestHarness` plus one end-to-end example config so the shared Studio can validate the new metadata.

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

## Bus Channel Ownership

Domain-specific bus channel names belong in plugin manifests and experiment configs, not in Persephone core. Declare every channel a plugin reads or writes:

```python
PluginManifest(
    # ...
    bus_reads=["external_signal"],
    bus_writes=["plugin_state"],
)
```

Core solver wrappers must use `manifest.bus_reads` and `manifest.bus_writes` to move data through the bus. A plugin should not depend on another plugin object directly.
