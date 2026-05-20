# Core Architecture Notes

This document records the core rules that must hold before Persephone grows beyond the current SIR workbench.

## Scheduler Semantics

The v2 scheduler uses first-order operator splitting:

1. Every runtime reads from the committed bus snapshot for tick `N`.
2. Every runtime advances by the same validated elapsed interval.
3. Runtime writes go into the pending bus buffer.
4. The bus commits the pending buffer atomically for tick `N + 1`.
5. Observers and scheduler telemetry are emitted from the committed tick state.

`scheduler.sync_interval` controls the requested coupling interval. When it is `auto`, the scheduler uses the minimum solver `preferred_dt`. When it is numeric, the scheduler uses the smaller of the configured interval, optional `scheduler.dt`, each solver's `preferred_dt`, and remaining time to `t_end`.

`scheduler.splitting_order` exists so future tightly-coupled simulations can request Strang splitting, but v2 implements `first_order` first.

## Scheduler Telemetry

The scheduler emits telemetry as regular metric records with `solver_id = "scheduler"`. Current metrics include:

- `scheduler.wall_time_ms`
- `scheduler.sync_interval_used`
- `scheduler.solver_step_time_ms`

Telemetry tags include tick, sync interval, CFL-constrained status, and solver ids where relevant. This keeps performance and coupling diagnostics queryable through the same CLI/API/UI paths as domain metrics.

## Checkpoints

When `scheduler.checkpoint_every` is set, Persephone writes checkpoints under:

```text
runs/<run_id>/checkpoints/<tick>/
├── checkpoint.json
├── state.npz
├── state.json
├── bus.json
└── rng.json
```

Each checkpoint contains runtime state, committed bus snapshot, solver RNG states, logical time, config hash, plugin versions, and schema version. Full resume UX is intentionally left for a follow-up, but the artifact format is now present.

## Domain-Agnostic Bus Rule

Core engine code must not hardcode domain channel names such as `temperature_field`, `aerosol_grid`, `viral_fitness`, or `infection_map`.

Domain channel names belong in plugin manifests and experiment configs. Core wrappers must read from `manifest.bus_reads` and write to `manifest.bus_writes` only.

## State Support

The durable v2 storage path supports plain NumPy arrays first. Sparse matrices and masked arrays are part of the long-term state contract, but until full support lands they fail with explicit unsupported-state errors rather than obscure serialization failures.

## Plugin Trust Model

Python plugins are trusted code in v2. Installing or importing a plugin executes Python from that package. Remote plugin installation, marketplace publishing, WASM sandboxing, and untrusted plugin execution remain out of scope for v2 runtime.
