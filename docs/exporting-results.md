# Exporting Results

Persephone exports completed run records to CSV or Parquet.

## CLI

```bash
uv run persephone export sir-demo --format csv --output exports/sir-demo-csv
uv run persephone export sir-demo --format parquet --output exports/sir-demo-parquet
```

Each export writes:

- `metrics.csv` or `metrics.parquet`
- `events.csv` or `events.parquet`

The exported row counts match the source JSONL files.

## API

```http
GET /runs/{run_id}/export?format=csv
GET /runs/{run_id}/export?format=parquet
```

The API returns a zip archive containing metrics and events files.
