# Config Reference

Experiment configs are YAML files loaded into typed Pydantic models.

## Minimal Example

```yaml
name: sir_epidemic_baseline
seed: 42

scheduler:
  t_end: 24
  sync_interval: auto

solvers:
  - type: graph
    plugin: sir_epidemic
    version: ">=0.1.0"
    params:
      contact_graph: data/sir_contact_edges.csv
      n_nodes: 20
      initially_infected: [0, 10]
      p_infect: 0.6
      p_recover: 0.08
```

## Top-Level Fields

| Field | Required | Description |
|---|---:|---|
| `name` | Yes | Human-readable experiment name. |
| `description` | No | Optional description. |
| `seed` | Yes | Base seed used to derive deterministic solver seeds. |
| `scheduler` | Yes | Time horizon and stepping controls. |
| `solvers` | Yes | One or more plugin-backed solvers. |
| `observer` | No | Metric selection and emission cadence. |
| `storage` | No | Local artifact output settings. |
| `coupling` | No | Rules for resolving duplicate bus writes. |

## Scheduler

```yaml
scheduler:
  t_end: 24
  sync_interval: auto
```

- `t_end`: positive number, final logical time.
- `sync_interval`: `auto` or a positive number. Version 1 uses the active solver preferred step.
- `dt`: optional positive number for future solvers.
- `ensemble_size`: optional positive integer for future ensemble runs.

## Solver

```yaml
solvers:
  - type: graph
    plugin: sir_epidemic
    version: ">=0.1.0"
    params: {}
```

- `type`: one of `ode`, `pde`, `abm`, `graph`, `sde`, `hybrid`.
- `plugin`: entry-point name from `persephone.plugins`.
- `version`: Python package version specifier.
- `params`: plugin-specific parameters.

## SIR Plugin Parameters

| Parameter | Description |
|---|---|
| `contact_graph` | CSV path with `source,target,weight`; relative paths resolve from the config file. |
| `n_nodes` | Number of nodes in the graph. |
| `initially_infected` | Integer count sampled from the seed, or explicit list of infected node ids. |
| `p_infect` | Base infection probability, `0.0` to `1.0`. |
| `p_recover` | Recovery probability per tick, `0.0` to `1.0`. |

## Storage

```yaml
storage:
  artifacts_dir: runs
  metrics: true
  events: true
```

Version 1 writes local artifacts under `artifacts_dir/<run_id>/`.

## Coupling

```yaml
coupling:
  rules:
    states: last
```

Supported rules are `sum`, `mean`, `max`, `min`, and `last`.

