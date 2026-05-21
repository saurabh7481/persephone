# Heat Diffusion Plugin

The `heat_diffusion` plugin is the first v2 PDE plugin. It models 2D heat diffusion over a rectangular grid with an explicit finite-difference step.

## Run

```bash
uv run persephone run configs/examples/heat_diffusion.yaml --run-id heat-demo
```

## Model

The state contains:

- `temperature`: 2D `float64` field.
- `alpha`: thermal diffusivity.
- `dx`, `dy`: grid spacing.

The solver uses zero-flux boundary behavior through edge padding and enforces the explicit 2D CFL stability limit before every step.

## Metrics

The observer emits:

- `temperature_min`
- `temperature_max`
- `temperature_mean`
- `total_heat`
- `center_temperature`

## Field Artifacts

Final and checkpointed 2D arrays are exposed as field artifacts:

```bash
uv run persephone fields list heat-demo
uv run persephone fields export heat-demo 'final_state:heat_diffusion#0.temperature' --output exports/temperature.csv
```

API clients can use:

```http
GET /runs/{run_id}/fields
GET /runs/{run_id}/fields/{field_id}?format=csv
```
