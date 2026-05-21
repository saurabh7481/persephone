# Run Comparison

Run comparison aligns two completed runs by metric name and logical time.

## CLI

```bash
uv run persephone compare run-a run-b --metric infected_count
```

The CLI reports peak value, final value, and area under the curve for each run.

## API

```http
GET /compare?run=run-a&run=run-b&metric=infected_count
```

The response contains aligned points and per-run summaries. Missing time points are represented as `null` values so clients can decide how to render gaps.
