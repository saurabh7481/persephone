# Persephone v0.2 Quality Gate

Version 0.2 focuses on the headless local research workbench.

## Included

- Local FastAPI service for run control, streaming, sweeps, comparison, exports, and field artifacts.
- CSV and Parquet export for metrics and events.
- Heat diffusion PDE plugin with CFL stability checks and 2D field artifacts.
- Field artifact listing and CSV/NPY export from final states and checkpoints.
- Plugin scaffold command for trusted Python plugin packages.
- Core hardening for typed records, telemetry, checkpoint groundwork, storage sinks, coupling validation, and SDK contract checks.
- MVP SvelteKit UI kept compiling as a smoke-test client.

## Quality Gate

Run before tagging v0.2:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache uv sync
UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest --cov=persephone --cov=persephone_sdk
UV_CACHE_DIR=/private/tmp/uv-cache uv run ruff check .
UV_CACHE_DIR=/private/tmp/uv-cache uv run ruff format --check .
UV_CACHE_DIR=/private/tmp/uv-cache uv run mypy src sdk/src plugins/persephone-plugin-sir-epidemic/src plugins/persephone-plugin-heat-diffusion/src
cd ui && bun run check && bun run lint && bun run test:unit && bun run build
```

Manual smoke commands:

```bash
uv run persephone run configs/examples/sir_epidemic.yaml --run-id v02-sir
uv run persephone run configs/examples/heat_diffusion.yaml --run-id v02-heat
uv run persephone sweep configs/examples/sir_p_infect_sweep.yaml
uv run persephone export v02-sir --format csv --output exports/v02-sir-csv
uv run persephone export v02-sir --format parquet --output exports/v02-sir-parquet
uv run persephone fields list v02-heat
```
