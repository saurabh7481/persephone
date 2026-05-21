# Engine Runtime Interface

The runtime interface is the boundary between the product/API layer and the simulation executor.

In v3, the implementation is `PythonSimulationRuntime`, which adapts the existing `PersephoneEngine`. Later, a Rust runtime or accelerated kernel layer should implement the same concepts without changing the UI-facing API.

## Responsibilities

A runtime can:

- validate an experiment config,
- start a run,
- stream persisted or live records,
- cancel a run if the backend supports cancellation,
- list run artifacts,
- report runtime capabilities.

## Capability Metadata

Every runtime reports:

- backend name,
- backend version,
- live frame support,
- replay support,
- pause/resume support,
- recommended frame rate.

Run manifests also include `runtime_backend` and `runtime_version` so artifacts remain interpretable after the runtime implementation changes.

## Rust Path

Rust should first enter as an implementation of this runtime boundary, or as accelerated kernels under the Python runtime. The external API should remain based on language-neutral records: runs, metrics, events, frames, artifacts, and capabilities.
