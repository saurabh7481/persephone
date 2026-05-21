# Simulation Frame Contract

Simulation frames are normalized visualization records used by the Studio UI for live playback and replay.

The engine emits domain state. Plugin renderers adapt that state into frame records. The UI renders frame records without hardcoding a plugin domain.

## Shared Fields

Every frame has:

- `kind`: frame kind, such as `field` or `graph`.
- `run_id`: run identifier.
- `frame_id`: stable frame identifier.
- `t`: logical simulation time.
- `tick`: scheduler tick.
- `solver_id`: producing solver runtime.
- `source`: `live`, `replay`, `checkpoint`, or `final_state`.
- `schema_version`: frame schema version.

## FieldFrame

`FieldFrame` represents a 2D scalar field.

It contains:

- field name,
- shape,
- dtype,
- min/max bounds,
- units,
- visualization hints,
- inline values for small frames or a payload reference for large frames.

This is the first frame target for heat diffusion playback, but the contract is not heat-specific.

## GraphFrame

`GraphFrame` represents a graph state.

It contains:

- nodes,
- edges,
- optional positions,
- optional node state,
- optional edge weights,
- visualization hints.

This is the first frame target for contact-network playback, but the contract is not tied to any one graph domain.

## Size Policy

Small frame payloads may be sent inline. Large frames should use `payload_ref`, pointing to an artifact such as JSON, NPZ, NPY, Zarr, or Parquet.
