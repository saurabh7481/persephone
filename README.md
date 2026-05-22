# Persephone

Persephone is a local-first, plugin-driven simulation platform. Version 4 turns the Studio into an interpretable analysis workbench: plugins can declare semantics for entities, states, metrics, and recommended views so the shared `/runs/{run_id}` page can adapt across domains without bespoke UI rewrites.

See [Persephone.md](Persephone.md) for the architecture and [docs/tasks/v1_tasks.md](docs/tasks/v1_tasks.md) for the implementation checklist.
Core scheduler, checkpoint, telemetry, and state-contract notes live in [docs/core-architecture.md](docs/core-architecture.md).

## Quickstart

Requirements:

- Python 3.11+
- `uv`

For Docker-only local usage, skip to [Docker Quickstart](#docker-quickstart).

Install the workspace packages, including the editable first-party plugins:

```bash
uv sync
```

Validate the example config:

```bash
uv run persephone validate configs/examples/sir_epidemic.yaml
```

Confirm plugin discovery:

```bash
uv run persephone plugins list
```

Run the example simulation:

```bash
uv run persephone run configs/examples/sir_epidemic.yaml --run-id sir-demo
```

Run the PDE example:

```bash
uv run persephone run configs/examples/heat_diffusion.yaml --run-id heat-demo
```

Run the cross-domain v4 examples:

```bash
uv run persephone run configs/examples/market_stress.yaml --run-id market-demo
uv run persephone run configs/examples/dependency_workflow.yaml --run-id workflow-demo
```

Inspect the output:

```bash
uv run persephone runs show runs/sir-demo
uv run persephone runs metrics runs/sir-demo --metric infected_count
uv run persephone replay runs/sir-demo
uv run persephone fields list heat-demo
uv run persephone export sir-demo --format csv --output exports/sir-demo-csv
uv run persephone export sir-demo --format parquet --output exports/sir-demo-parquet
```

Start the local API:

```bash
uv run persephone api --host 127.0.0.1 --port 8787
```

Start the MVP UI in another terminal:

```bash
cd ui
bun run dev -- --host 127.0.0.1
```

## Docker Quickstart

Run the API and UI together:

```bash
docker compose up --build
```

Open the UI at:

```text
http://127.0.0.1:5173/runs
```

The API is available at:

```text
http://127.0.0.1:8787/health
```

Run the stack in the background:

```bash
docker compose up --build -d
```

Stop it:

```bash
docker compose down
```

The API container includes the CLI:

```bash
docker compose exec api persephone run configs/examples/sir_epidemic.yaml --run-id docker-demo
```

More detail is in [docs/docker.md](docs/docker.md).

## Package Boundaries

Persephone is developed as a monorepo for Version 1, but each package has a clear boundary:

- `src/persephone`: engine, config validation, scheduler, registry, storage, CLI, and reusable solver kernels.
- `sdk/src/persephone_sdk`: public plugin SDK contracts: `World`, `Solver`, `Observer`, `Renderer`, `PluginManifest`, and `PluginTestHarness`.
- `plugins/persephone-plugin-sir-epidemic`: graph SIR plugin, discovered through the same `persephone.plugins` entry point used by future external plugins.
- `plugins/persephone-plugin-heat-diffusion`: 2D PDE heat diffusion plugin with field artifacts.
- `plugins/persephone-plugin-market-stress`: synthetic sector-correlation fixture proving dense graph semantics and matrix-first analysis.
- `plugins/persephone-plugin-dependency-workflow`: synthetic codebase workflow fixture proving hierarchy/table inspection with the shared contracts.

The engine should not directly import plugin modules. Plugins are installed packages and are discovered through entry points.

## Version 2 Plugin Trust Model

Version 2 plugins are trusted Python code. Installing a plugin executes Python from that package, exactly like installing any other Python dependency. Only install plugins you trust.

Sandboxing, remote plugin installation, plugin registry publishing, and untrusted plugin execution are later-phase features.

## Example Data

The first runnable data source is synthetic:

```text
configs/examples/data/sir_contact_edges.csv
```

It uses this CSV schema:

```csv
source,target,weight
0,1,1.0
1,2,0.9
```

The graph is synthetic to keep the first run deterministic, offline, fast, and license-clean.

The heat diffusion example uses a generated in-memory 2D hotspot field. You can create an `.npy` initial condition file with:

```bash
uv run persephone examples generate-heat-field --output configs/examples/data/heat_initial.npy
```

## Run Artifacts

A completed run writes:

```text
runs/<run_id>/
├── manifest.json
├── metrics.jsonl
├── events.jsonl
├── final_state.npz
├── final_state.json
├── exports/
└── checkpoints/
```

- `manifest.json`: run id, status, config hash, plugin versions, seed plan, engine/SDK versions, and environment metadata.
- `metrics.jsonl`: one JSON metric record per emitted metric per tick.
- `events.jsonl`: discrete events such as infection and recovery.
- `final_state.npz`: NumPy arrays for final solver state.
- `final_state.json`: metadata for final-state arrays.
- `checkpoints/`: optional checkpoint snapshots when `scheduler.checkpoint_every` is configured.
- `exports/`: optional CSV, Parquet, or field downloads created by the CLI/API.

## V4 Semantics And Interpretation

Version 4 plugins can enrich the shared analysis surface through `PluginManifest.semantics` and `Observer.explain(...)`.

- `entity_schemas`, `state_schema`, `metric_schema`, and `event_schema` give the UI human-facing labels instead of raw ids.
- `view_capabilities` and `preferred_view` tell the run page whether a domain should open in a network, matrix, hierarchy, table, timeline, or heatmap flow.
- `explanation_capabilities` plus deterministic fact packets let the same explanation panels work for replay and live runs.
- `interpretation.mode: rules_only` is the default recommendation for shipping evidence-backed summaries without any LLM dependency.

See [docs/plugin-authoring.md](docs/plugin-authoring.md) for migration guidance and [docs/tasks/v4_tasks.md](docs/tasks/v4_tasks.md) for the v4 delivery checklist.

## Reproducibility

Persephone derives deterministic per-solver seed streams from the experiment seed. For this v1 local engine:

- Same config, seed, engine version, SDK version, plugin version, and lockfile should produce the same metric records.
- Changing the seed should change stochastic outcomes for stochastic simulations.
- The run manifest records the config hash, seed plan, dependency lock hash, and plugin versions.

Known limits:

- Reproducibility has only been verified for the local Python execution path.
- Distributed execution, GPU kernels, and cross-platform numeric drift are not part of Version 1.

## Troubleshooting

If `persephone plugins list` does not show `sir_epidemic`, run:

```bash
uv sync
```

Then check the plugin package is a workspace member in `pyproject.toml` and exposes:

```toml
[project.entry-points."persephone.plugins"]
sir_epidemic = "persephone_sir_epidemic:SIREpidemicPlugin"
```

If validation says a data file is missing, paths in config files are resolved relative to the config file location.
