from __future__ import annotations

import json
from pathlib import Path

from persephone_sdk.plugin import Observer, PluginManifest, Renderer, Solver, World

from persephone.config.models import ExperimentConfig, SchedulerConfig, SolverConfig
from persephone.core.explanations import ExplanationPacket
from persephone.core.run import RunContext


def test_experiment_config_accepts_interpretation_settings() -> None:
    config = ExperimentConfig.model_validate(
        {
            "name": "interpretation-test",
            "seed": 17,
            "scheduler": {"t_end": 3.0},
            "solvers": [{"type": "graph", "plugin": "demo", "version": ">=0.1.0"}],
            "interpretation": {
                "mode": "minimal_ai",
                "every_n_ticks": 2,
                "on_milestone": True,
                "on_complete": True,
                "max_input_facts": 3,
                "max_output_tokens": 12,
                "store_records": True,
            },
        }
    )

    assert config.interpretation.mode == "minimal_ai"
    assert config.interpretation.every_n_ticks == 2
    assert config.interpretation.max_input_facts == 3
    assert config.interpretation.max_output_tokens == 12
    assert config.interpretation.store_records is True


def test_interpretation_service_returns_disabled_summary_when_mode_is_off(tmp_path: Path) -> None:
    from persephone.core.interpretation import InterpretationService

    context = run_context("off")
    packet = run_packet()

    result = InterpretationService(tmp_path / "runs").interpret_run(
        context=context,
        packets=[packet],
    )

    assert result.summary is None
    assert result.mode_requested == "off"
    assert result.mode_applied == "off"
    assert result.cached is False
    assert result.label == "Interpretation disabled"
    assert result.facts[0].kind == "trend"


def test_interpretation_service_uses_rules_only_summary(tmp_path: Path) -> None:
    from persephone.core.interpretation import InterpretationService

    context = run_context("rules_only")
    packet = run_packet()

    result = InterpretationService(tmp_path / "runs").interpret_run(
        context=context,
        packets=[packet],
    )

    assert result.mode_requested == "rules_only"
    assert result.mode_applied == "rules_only"
    assert result.label == "Deterministic interpretation"
    assert result.summary is not None
    assert result.summary.summary.startswith("Population increased")
    assert result.summary.evidence[0].label == "population_sum"


def test_interpretation_service_caches_minimal_ai_results_and_enforces_budget(
    tmp_path: Path,
) -> None:
    from persephone.core.interpretation import InterpretationService

    calls: list[dict[str, object]] = []

    def fake_ai(prompt: dict[str, object]) -> str:
        calls.append(prompt)
        return (
            "Population keeps climbing because one metric crossed the baseline and remained elevated"
        )

    context = run_context("minimal_ai", store_records=True)
    packet = run_packet(extra_fact=True)
    service = InterpretationService(tmp_path / "runs", ai_paraphraser=fake_ai)

    first = service.interpret_run(context=context, packets=[packet])
    second = service.interpret_run(context=context, packets=[packet])

    assert first.mode_requested == "minimal_ai"
    assert first.mode_applied == "minimal_ai"
    assert first.cached is False
    assert second.cached is True
    assert len(calls) == 1
    assert len(calls[0]["facts"]) == 1
    assert first.summary is not None
    assert len(first.summary.summary.split()) <= context.config_snapshot["interpretation"][
        "max_output_tokens"
    ]

    cache_lines = [
        json.loads(line)
        for line in (tmp_path / "runs" / context.run_id / "explanations" / "interpretations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert cache_lines[0]["mode_applied"] == "minimal_ai"
    assert cache_lines[0]["prompt"]["facts"][0]["title"] == "Population is rising"


def run_context(
    mode: str,
    *,
    store_records: bool = False,
) -> RunContext:
    class WorldStub(World):
        def schema(self) -> dict[str, tuple[int, ...]]:
            return {"population": (1,)}

        def init(self, params: dict[str, object], seed: int):
            return {}

        def reset(self):
            return {}

    class SolverStub(Solver):
        @property
        def preferred_dt(self) -> float:
            return 1.0

        def step(self, state, dt: float, bus: object):
            return state, dt

    class ObserverStub(Observer):
        def observe(self, state, t: float, run_id: str):
            return []

    class RendererStub(Renderer):
        def viz_schema(self) -> dict[str, object]:
            return {"type": "graph"}

    manifest = PluginManifest(
        name="demo",
        version="0.1.0",
        paradigm="graph",
        world=WorldStub,
        solver=SolverStub,
        observer=ObserverStub,
        renderer=RendererStub,
        bus_reads=[],
        bus_writes=[],
    )
    config = ExperimentConfig(
        name="interpretation-test",
        seed=7,
        scheduler=SchedulerConfig(t_end=1.0, sync_interval=1.0),
        solvers=[SolverConfig(type="graph", plugin="demo", version=">=0.1.0")],
        interpretation={
            "mode": mode,
            "every_n_ticks": 1,
            "on_milestone": True,
            "on_complete": True,
            "max_input_facts": 1,
            "max_output_tokens": 8,
            "store_records": store_records,
        },
    )
    return RunContext.create(config, {"demo": manifest}, run_id="interpret-run")


def run_packet(*, extra_fact: bool = False) -> ExplanationPacket:
    facts = [
        {
            "kind": "trend",
            "title": "Population is rising",
            "summary": "Population increased above the initial baseline.",
            "severity": "warning",
            "evidence": [{"label": "population_sum", "value": 2.0}],
            "related_ids": ["population"],
            "t": 1.0,
        }
    ]
    if extra_fact:
        facts.append(
            {
                "kind": "milestone",
                "title": "Baseline crossed",
                "summary": "Population exceeded the configured threshold.",
                "severity": "info",
                "evidence": [{"label": "threshold", "value": 1.0}],
                "related_ids": ["population"],
                "t": 1.0,
            }
        )
    return ExplanationPacket.model_validate(
        {
            "run_id": "interpret-run",
            "solver_id": "demo#0",
            "scope": "run",
            "t": 1.0,
            "tick": 1,
            "facts": facts,
        }
    )
