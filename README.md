# Persephone

Persephone is a local-first, plugin-driven simulation platform. Version 1 proves the full loop with a graph-based SIR epidemic simulation: validate a YAML config, discover a plugin, run the simulation, write run artifacts, inspect metrics, and replay results from the CLI.

See [Persephone.md](Persephone.md) for the architecture and [docs/tasks/v1_tasks.md](docs/tasks/v1_tasks.md) for the implementation checklist.
Core scheduler, checkpoint, telemetry, and state-contract notes live in [docs/core-architecture.md](docs/core-architecture.md).

## Quickstart

Requirements:

- Python 3.11+
- `uv`

For Docker-only local usage, skip to [Docker Quickstart](#docker-quickstart).

Install the workspace packages, including the editable SIR plugin:

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

Inspect the output:

```bash
uv run persephone runs show runs/sir-demo
uv run persephone runs metrics runs/sir-demo --metric infected_count
uv run persephone replay runs/sir-demo
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
- `plugins/persephone-plugin-sir-epidemic`: first plugin package, discovered through the same `persephone.plugins` entry point used by future external plugins.

The engine should not directly import plugin modules. Plugins are installed packages and are discovered through entry points.

## Version 1 Plugin Trust Model

Version 1 plugins are trusted Python code. Installing a plugin executes Python from that package, exactly like installing any other Python dependency. Only install plugins you trust.

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

## Run Artifacts

A completed run writes:

```text
runs/<run_id>/
├── manifest.json
├── metrics.jsonl
├── events.jsonl
├── final_state.npz
├── final_state.json
└── checkpoints/
```

- `manifest.json`: run id, status, config hash, plugin versions, seed plan, engine/SDK versions, and environment metadata.
- `metrics.jsonl`: one JSON metric record per emitted metric per tick.
- `events.jsonl`: discrete events such as infection and recovery.
- `final_state.npz`: NumPy arrays for final solver state.
- `final_state.json`: metadata for final-state arrays.
- `checkpoints/`: optional checkpoint snapshots when `scheduler.checkpoint_every` is configured.

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
