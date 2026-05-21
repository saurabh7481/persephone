# Persephone MVP UI Guide

The current UI is an MVP smoke-test client for the local API. It is intentionally not the final product surface. Use it to verify API flows while the core engine, artifacts, exports, and plugins stabilize.

## Start

```bash
uv run persephone api --host 127.0.0.1 --port 8787
cd ui
bun run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/runs`.

## Current Capabilities

- List local runs.
- Start the bundled SIR experiment.
- View metric and event records.
- Stream live run metrics.
- Create a scalar parameter sweep.
- Compare two runs with an overlay chart.

## Design Direction

Future UI work should target the stable headless API rather than expanding this MVP surface. New core capabilities should land in CLI/API first, then be incorporated into the redesigned UI.
