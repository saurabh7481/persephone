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
