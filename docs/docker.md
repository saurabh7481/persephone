# Docker Quickstart

Persephone can run as a local two-container stack:

- `api`: Python engine, plugin registry, local API, and CLI.
- `ui`: SvelteKit UI served by the Node adapter through Bun.

The stack is intended for local use. Kubernetes manifests can build on the same images later.

## Requirements

- Docker Desktop or another Docker engine.
- Docker Compose.

## Start Everything

From the repository root:

```bash
docker compose up --build
```

Open:

- UI: `http://127.0.0.1:5173/runs`
- API health: `http://127.0.0.1:8787/health`

Run in the background:

```bash
docker compose up --build -d
```

Stop:

```bash
docker compose down
```

## Run a Simulation in Docker

The API container also has the `persephone` CLI available:

```bash
docker compose exec api persephone run configs/examples/sir_epidemic.yaml --run-id docker-demo
docker compose exec api persephone runs show docker-demo
docker compose exec api persephone runs metrics docker-demo --metric infected_count
```

Run artifacts are persisted to the host `runs/` directory through this volume:

```yaml
./runs:/app/runs
```

## Rebuild After Changes

```bash
docker compose build
docker compose up -d
```

If dependencies change, rebuild without cache:

```bash
docker compose build --no-cache
```

## Image Layout

- API image: `docker/api.Dockerfile`
  - Base: `ghcr.io/astral-sh/uv:python3.14-bookworm-slim`
  - Installs the Python workspace with `uv sync --frozen --no-dev`
  - Starts `persephone api --host 0.0.0.0 --port 8787`

- UI image: `docker/ui.Dockerfile`
  - Base: `oven/bun:1.2.23`
  - Installs with `bun install --frozen-lockfile`
  - Builds SvelteKit with `@sveltejs/adapter-node`
  - Starts `bun build/index.js` on port `3000`, mapped to host port `5173`

## Local Security

The v2 API remains local-first and unauthenticated. The compose file publishes the API on host port `8787`; avoid exposing it on public networks until auth and plugin sandboxing exist.
