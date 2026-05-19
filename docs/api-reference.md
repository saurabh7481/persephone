# Persephone Local API Reference

Persephone v2 starts with a local FastAPI service for driving the Python engine from a UI or local tool.

## Start the API

```bash
uv run persephone api --host 127.0.0.1 --port 8787
```

The API is local-first and unauthenticated in v2. Bind it to `127.0.0.1` or `localhost` for trusted local workflows. Persephone prints a warning if the API is bound to a non-localhost interface because v2 does not include production auth, tenant isolation, or untrusted plugin sandboxing.

## Endpoints

### `GET /health`

Returns service status and engine version.

### `GET /plugins`

Lists installed simulation plugins discovered through the Persephone plugin entry point.

### `POST /runs`

Starts a simulation run in a background thread.

Payload:

```json
{
  "run_id": "optional-run-id",
  "config": {
    "name": "sir_epidemic_baseline",
    "seed": 42,
    "scheduler": { "t_end": 24, "sync_interval": "auto" },
    "solvers": []
  }
}
```

The `config` object uses the same experiment schema as the YAML configuration files.

### `GET /runs`

Lists active and completed runs from the local run catalog. Optional `status` values include `pending`, `running`, `cancelling`, `cancelled`, `completed`, and `failed`.

### `GET /runs/{run_id}`

Returns status, manifest summary, artifact path, final time, plugins, config hash, and error message if present.

### `GET /runs/{run_id}/metrics`

Returns metric JSONL records as JSON. Use `?metric=infected_count` to filter by metric name.

### `GET /runs/{run_id}/events`

Returns event JSONL records as JSON.

### `GET /runs/{run_id}/stream`

Streams metric records as Server-Sent Events with `event: metric`.

### `POST /runs/{run_id}/cancel`

Requests cooperative cancellation for an active run. Cancellation is checked at scheduler tick boundaries.
