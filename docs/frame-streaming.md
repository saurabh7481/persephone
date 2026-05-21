# Frame Streaming

Persephone v3 exposes replay-first and live-ready frame transport through normalized frame
contracts.

## Replay Artifacts

Each run writes frame replay metadata under:

- `runs/<run_id>/frames/index.json`
- `runs/<run_id>/frames/frames.jsonl`
- `runs/<run_id>/frames/payloads/*.npz` for large field payloads

The run manifest links this with `frame_artifacts_path: "frames/index.json"`.

Small frames are stored inline in `frames.jsonl`. Large field frames keep the frame metadata in
JSONL and move numeric values to a compressed NPZ payload referenced by `payload_ref`.

## HTTP API

- `GET /runs/{run_id}/frames` lists replayable frames.
- `GET /runs/{run_id}/frames/{frame_id}` returns one hydrated frame.
- `GET /runs/{run_id}/frames/stream` streams Server-Sent Events.

Frame list queries support `kind`, `t_min`, `t_max`, `solver_id`, and `max_count`.

## SSE Contract

SSE events use monotonic `id` values while a run is managed by the local API process. Clients can
resume with `Last-Event-ID` or the `last_event_id` query parameter.

Event names:

- `frame`
- `metric`
- `event`
- `status`
- `error`
- `heartbeat`

The in-process stream buffer is bounded. If the UI falls behind, older buffered live events can be
dropped and replay should recover from persisted artifacts after completion.

## WebSocket Later

SSE is the v3 starting point because it is simple, reconnectable, and works well for one-way run
playback. WebSocket should supplement it when the Studio needs bidirectional controls such as
backend pause/resume, collaborative cursors, remote command acknowledgement, or high-frequency
binary frame transport.
