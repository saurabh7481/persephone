# Persephone v0.1 Release Checklist

## Scope

Version 0.1 is the first local-first vertical slice:

- Plugin SDK contracts.
- Entry-point plugin discovery.
- Typed YAML config validation.
- Double-buffered in-memory bus.
- Run provenance and local artifacts.
- Graph SIR kernel.
- Local scheduler and engine facade.
- `sir_epidemic` plugin.
- Synthetic ready-to-run SIR example.
- CLI validation, run, inspect, metrics, replay, and example graph generation.

## Verification Commands

- [ ] `uv sync`
- [ ] `uv run pytest --cov`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run mypy src sdk/src plugins/persephone-plugin-sir-epidemic/src`
- [ ] `uv run persephone validate configs/examples/sir_epidemic.yaml`
- [ ] `uv run persephone plugins list`
- [ ] `uv run persephone run configs/examples/sir_epidemic.yaml --run-id release-smoke`
- [ ] `uv run persephone runs show runs/release-smoke`
- [ ] `uv run persephone runs metrics runs/release-smoke --metric infected_count`
- [ ] `uv run persephone replay runs/release-smoke`

## Manual Checks

- [ ] `persephone plugins list` shows `sir_epidemic 0.1.0`.
- [ ] Same-seed runs produce identical `metrics.jsonl`.
- [ ] Different-seed runs produce different stochastic outcomes.
- [ ] `manifest.json` records config hash, plugin versions, seed plan, engine version, SDK version, and status.
- [ ] `metrics.jsonl` contains SIR metrics for every tick.
- [ ] README quickstart works from a clean checkout.

## Known Limits

- No API server or UI in v0.1.
- No plugin sandbox.
- No Redis/TimescaleDB/ClickHouse backends.
- No parameter sweeps.
- No checkpoint/resume.

