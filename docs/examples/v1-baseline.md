# V1 Baseline Run

This is the known-good Version 1 baseline used before starting Version 2 work.

## Command

```bash
uv run persephone run configs/examples/sir_epidemic.yaml --run-id v2-baseline
```

## Summary

- Run id: `v2-baseline`
- Status: `completed`
- Artifact directory: `runs/v2-baseline`
- Config: `configs/examples/sir_epidemic.yaml`
- Config hash: `b4ae590027caf0b557423abf4522ad0b0b96543daf38a1f5ca57cc7a60a7c42b`
- Engine version: `0.1.0`
- SDK version: `0.1.0`
- Plugin: `sir_epidemic` version `0.1.0`
- Seed: `42`
- Final simulation time: `24.0`
- Metric rows: `144`
- Event rows: `34`

## Final Metrics

At `t=24.0`:

- `susceptible_count`: `0.0`
- `infected_count`: `4.0`
- `recovered_count`: `16.0`
- `new_infections`: `0.0`
- `new_recoveries`: `0.0`
- `r_effective_estimate`: `0.0`

## Notes

This baseline verifies that the v1 SIR plugin and local artifact writer still produce a complete run before the v2 API, catalog, streaming, and UI work begins.
