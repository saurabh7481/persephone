# Parameter Sweeps

Persephone v2 supports sequential scalar parameter sweeps over dotted config paths.

## Example

```bash
uv run persephone sweep configs/examples/sir_p_infect_sweep.yaml
```

The example sweeps:

```text
solvers[0].params.p_infect
```

across `0.2`, `0.4`, and `0.6`.

Each child run is written under the configured artifact root and linked back to the sweep id in its manifest. The sweep manifest is written to `runs/<sweep_id>/sweep.json`.

## API

```http
POST /sweeps
```

with:

```json
{
  "name": "Infection probability sweep",
  "parameter": "solvers[0].params.p_infect",
  "values": [0.2, 0.4, 0.6],
  "base_config": {}
}
```
