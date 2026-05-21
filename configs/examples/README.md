# Persephone Example Configs

## `sir_epidemic.yaml`

Runs the first Version 1 plugin, `sir_epidemic`, against a synthetic 20-node contact graph.

The data file is `data/sir_contact_edges.csv`, with columns:

- `source`: integer source node id
- `target`: integer target node id
- `weight`: contact strength from `0.0` to `1.0`

The graph is synthetic by design. It avoids network access, API keys, and licensing ambiguity while still producing non-trivial epidemic spread for tests and demos.

## `sir_p_infect_sweep.yaml`

Runs the same SIR model three times while sweeping `solvers[0].params.p_infect` across `0.2`, `0.4`, and `0.6`.

```bash
uv run persephone sweep configs/examples/sir_p_infect_sweep.yaml
```

## `heat_diffusion.yaml`

Runs the `heat_diffusion` PDE plugin over a 12x12 2D temperature grid with a center hotspot.

```bash
uv run persephone run configs/examples/heat_diffusion.yaml --run-id heat-demo
uv run persephone fields list heat-demo
```

Generate a custom `.npy` initial condition file:

```bash
uv run persephone examples generate-heat-field --output configs/examples/data/heat_initial.npy
```
