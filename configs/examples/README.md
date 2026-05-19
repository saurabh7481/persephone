# Persephone Example Configs

## `sir_epidemic.yaml`

Runs the first Version 1 plugin, `sir_epidemic`, against a synthetic 20-node contact graph.

The data file is `data/sir_contact_edges.csv`, with columns:

- `source`: integer source node id
- `target`: integer target node id
- `weight`: contact strength from `0.0` to `1.0`

The graph is synthetic by design. It avoids network access, API keys, and licensing ambiguity while still producing non-trivial epidemic spread for tests and demos.

