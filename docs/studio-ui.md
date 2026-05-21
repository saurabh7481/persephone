# Persephone Studio UI

The v3 Studio UI is designed as a simulation instrument rather than a marketing surface. The
playback viewport is the center of gravity; experiment creation, frame inspection, metrics, events,
and artifact workflows orbit it.

## Product Principles

- Instrument-like
- Calm
- Dense
- Readable
- Non-technical default
- Technical on demand
- Playback centered

## Architecture

- `ui/src/lib/studio/tokens.ts` defines Studio principles, token groups, and contrast helpers.
- `ui/src/lib/components/studio/` contains Persephone-specific wrappers around the shadcn-svelte
  foundation.
- `ui/src/lib/studio/playback.ts` contains a source-agnostic playback store for live SSE and replay
  frames.
- The app shell uses a persistent top bar, icon rail, contextual workflow panel, and constrained
  workbench regions.

## Layout Model

Run detail pages use four workbench regions:

- Left panel: run context and playback controls.
- Center viewport: live/replay playback surface.
- Right inspector: selected frame/object details.
- Bottom dock: metrics, events, frames, artifacts, logs, and manifest.

The shell collapses to a horizontal rail and single-column workbench on smaller screens.
