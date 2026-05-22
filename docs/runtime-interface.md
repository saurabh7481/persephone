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

In v4, that runtime boundary also carries semantic and interpretation artifacts without letting AI into the deterministic stepping path. The runtime is responsible for surfacing:

- plugin semantic metadata attached to runs,
- replayable frame artifacts that keep entity labels and view hints intact,
- deterministic explanation fact packets,
- optional cached interpretation outputs derived from those facts.

## Capability Metadata

Every runtime reports:

- backend name,
- backend version,
- live frame support,
- replay support,
- pause/resume support,
- recommended frame rate.

Run manifests also include `runtime_backend` and `runtime_version` so artifacts remain interpretable after the runtime implementation changes.

Interpretation remains downstream of simulation. A runtime may expose rules-only or minimal-AI summaries, but those summaries must consume compact deterministic fact packets rather than mutating or steering simulation state.

## Rust Path

Rust should first enter as an implementation of this runtime boundary, or as accelerated kernels under the Python runtime. The external API should remain based on language-neutral records: runs, metrics, events, frames, artifacts, and capabilities.
