from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from persephone.config.models import InterpretationConfig
from persephone.core.explanations import (
    ExplanationFact,
    ExplanationPacket,
    ExplanationSummary,
    summarize_explanation_packet,
)
from persephone.core.run import RunContext

InterpretationMode = Literal["off", "rules_only", "minimal_ai"]
AiParaphraser = Callable[[dict[str, object]], str]


class InterpretationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    scope: Literal["run", "frame", "selection"]
    t: float = Field(ge=0)
    tick: int = Field(ge=0)
    frame_id: str | None = None
    selection_id: str | None = None
    mode_requested: InterpretationMode
    mode_applied: InterpretationMode
    label: str = Field(min_length=1)
    cached: bool = False
    facts: list[ExplanationFact] = Field(default_factory=list)
    summary: ExplanationSummary | None = None


class InterpretationService:
    def __init__(
        self,
        artifact_root: str | Path = "runs",
        *,
        ai_paraphraser: AiParaphraser | None = None,
    ) -> None:
        self.artifact_root = Path(artifact_root)
        self.ai_paraphraser = ai_paraphraser

    def interpret_run(
        self,
        *,
        context: RunContext,
        packets: list[ExplanationPacket],
        completed: bool = True,
    ) -> InterpretationResult:
        packet = _latest_packet(packet for packet in packets if packet.scope == "run")
        return self._interpret_packet(context=context, packet=packet, completed=completed)

    def interpret_frame(
        self,
        *,
        context: RunContext,
        packets: list[ExplanationPacket],
        frame_id: str,
        completed: bool = True,
    ) -> InterpretationResult:
        packet = _latest_packet(
            packet for packet in packets if packet.scope == "frame" and packet.frame_id == frame_id
        )
        return self._interpret_packet(context=context, packet=packet, completed=completed)

    def interpret_selection(
        self,
        *,
        context: RunContext,
        packets: list[ExplanationPacket],
        selection_id: str,
        completed: bool = True,
    ) -> InterpretationResult:
        packet = _latest_packet(
            packet
            for packet in packets
            if packet.scope == "selection" and packet.selection_id == selection_id
        )
        return self._interpret_packet(context=context, packet=packet, completed=completed)

    def _interpret_packet(
        self,
        *,
        context: RunContext,
        packet: ExplanationPacket,
        completed: bool,
    ) -> InterpretationResult:
        config = InterpretationConfig.model_validate(context.config_snapshot.get("interpretation", {}))
        facts = list(packet.facts)
        if config.mode == "off":
            return InterpretationResult(
                run_id=packet.run_id,
                scope=packet.scope,
                t=packet.t,
                tick=packet.tick,
                frame_id=packet.frame_id,
                selection_id=packet.selection_id,
                mode_requested="off",
                mode_applied="off",
                label="Interpretation disabled",
                cached=False,
                facts=facts,
                summary=None,
            )

        deterministic_summary = packet.summary or summarize_explanation_packet(packet)
        if config.mode == "rules_only":
            return InterpretationResult(
                run_id=packet.run_id,
                scope=packet.scope,
                t=packet.t,
                tick=packet.tick,
                frame_id=packet.frame_id,
                selection_id=packet.selection_id,
                mode_requested="rules_only",
                mode_applied="rules_only",
                label="Deterministic interpretation",
                cached=False,
                facts=facts,
                summary=deterministic_summary,
            )

        cache_key = self._cache_key(context=context, packet=packet, mode="minimal_ai")
        cached = self._read_cached_result(context=context, cache_key=cache_key)
        if cached is not None:
            return cached

        if not self._eligible_for_minimal_ai(packet=packet, config=config, completed=completed):
            return InterpretationResult(
                run_id=packet.run_id,
                scope=packet.scope,
                t=packet.t,
                tick=packet.tick,
                frame_id=packet.frame_id,
                selection_id=packet.selection_id,
                mode_requested="minimal_ai",
                mode_applied="rules_only",
                label="Deterministic interpretation",
                cached=False,
                facts=facts,
                summary=deterministic_summary,
            )

        if self.ai_paraphraser is None:
            return InterpretationResult(
                run_id=packet.run_id,
                scope=packet.scope,
                t=packet.t,
                tick=packet.tick,
                frame_id=packet.frame_id,
                selection_id=packet.selection_id,
                mode_requested="minimal_ai",
                mode_applied="rules_only",
                label="Deterministic interpretation",
                cached=False,
                facts=facts,
                summary=deterministic_summary,
            )

        prompt = self._prompt_packet(packet=packet, config=config)
        paraphrase = _truncate_words(
            self.ai_paraphraser(prompt),
            config.max_output_tokens,
        )
        ai_summary = ExplanationSummary(
            title=deterministic_summary.title,
            summary=paraphrase,
            severity=deterministic_summary.severity,
            evidence=deterministic_summary.evidence,
            fact_count=deterministic_summary.fact_count,
        )
        result = InterpretationResult(
            run_id=packet.run_id,
            scope=packet.scope,
            t=packet.t,
            tick=packet.tick,
            frame_id=packet.frame_id,
            selection_id=packet.selection_id,
            mode_requested="minimal_ai",
            mode_applied="minimal_ai",
            label="AI interpretation",
            cached=False,
            facts=facts,
            summary=ai_summary,
        )
        self._write_cached_result(context=context, cache_key=cache_key, result=result, prompt=prompt)
        return result

    def _prompt_packet(
        self,
        *,
        packet: ExplanationPacket,
        config: InterpretationConfig,
    ) -> dict[str, object]:
        selected_facts = sorted(
            packet.facts,
            key=lambda fact: (
                _severity_rank(fact.severity),
                fact.title.lower(),
            ),
            reverse=True,
        )[: config.max_input_facts]
        return {
            "run_id": packet.run_id,
            "scope": packet.scope,
            "tick": packet.tick,
            "t": packet.t,
            "facts": [
                {
                    "kind": fact.kind,
                    "title": fact.title,
                    "summary": fact.summary,
                    "severity": fact.severity,
                    "evidence": [evidence.model_dump(mode="json") for evidence in fact.evidence],
                }
                for fact in selected_facts
            ],
        }

    def _cache_path(self, context: RunContext) -> Path:
        return self.artifact_root / context.run_id / "explanations" / "interpretations.jsonl"

    def _read_cached_result(
        self,
        *,
        context: RunContext,
        cache_key: str,
    ) -> InterpretationResult | None:
        path = self._cache_path(context)
        if not path.exists():
            return None
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if payload.get("cache_key") != cache_key:
                continue
            result_payload = payload["result"]
            result_payload["cached"] = True
            return InterpretationResult.model_validate(result_payload)
        return None

    def _write_cached_result(
        self,
        *,
        context: RunContext,
        cache_key: str,
        result: InterpretationResult,
        prompt: dict[str, object],
    ) -> None:
        path = self._cache_path(context)
        path.parent.mkdir(parents=True, exist_ok=True)
        config = InterpretationConfig.model_validate(context.config_snapshot.get("interpretation", {}))
        record: dict[str, object] = {
            "cache_key": cache_key,
            "mode_requested": result.mode_requested,
            "mode_applied": result.mode_applied,
            "result": result.model_dump(mode="json"),
        }
        if config.store_records:
            record["prompt"] = prompt
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")

    def _cache_key(
        self,
        *,
        context: RunContext,
        packet: ExplanationPacket,
        mode: InterpretationMode,
    ) -> str:
        plugin_signature = ",".join(
            f"{name}:{version}" for name, version in sorted(context.plugin_versions.items())
        )
        return "|".join(
            [
                context.run_id,
                packet.scope,
                str(packet.tick),
                packet.frame_id or "",
                packet.selection_id or "",
                plugin_signature,
                mode,
            ]
        )

    def _eligible_for_minimal_ai(
        self,
        *,
        packet: ExplanationPacket,
        config: InterpretationConfig,
        completed: bool,
    ) -> bool:
        if packet.tick % config.every_n_ticks == 0:
            return True
        if config.on_milestone and any(fact.kind == "milestone" for fact in packet.facts):
            return True
        if config.on_complete and completed:
            return True
        return False


def _latest_packet(packets: Any) -> ExplanationPacket:
    ordered = sorted(
        packets,
        key=lambda packet: (packet.tick, packet.t),
    )
    if not ordered:
        raise ValueError("No explanation packet matched the requested scope")
    return ordered[-1]


def _truncate_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit])


def _severity_rank(severity: str) -> int:
    order = {
        "info": 0,
        "notice": 1,
        "warning": 2,
        "critical": 3,
    }
    return order.get(severity, 0)


__all__ = ["InterpretationResult", "InterpretationService"]
