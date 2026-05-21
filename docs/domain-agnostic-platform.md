# Domain-Agnostic Platform Invariant

Persephone is a plugin platform. Core API, CLI, SDK, shared frontend infrastructure, and Studio UI should not assume a specific plugin or simulation domain.

## Rule

Domain terms belong in:

- plugin packages,
- example configs,
- example docs,
- plugin-specific tests,
- explicit compatibility aliases.

Domain terms should not drive core behavior in:

- engine scheduling,
- API route logic,
- generic CLI commands,
- storage,
- export,
- replay,
- comparison,
- shared UI stores and API clients.

## Current v3 Guard

The test suite includes a domain-term leak test for shared platform paths. It catches common example-domain strings in core Python code, SDK code, and shared UI API infrastructure.

## Product Implication

The Studio UI should be generated from plugin metadata:

- parameter schemas drive experiment forms,
- renderer metadata drives visualization hints,
- frame contracts drive playback,
- metric schemas drive chart defaults,
- artifact indexes drive downloads and inspection.

SIR and heat diffusion remain important examples, but they are presets rather than platform assumptions.
