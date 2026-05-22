from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


Severity = Literal["info", "notice", "warning", "critical"]
ExplanationScope = Literal["run", "frame", "selection"]

SEVERITY_PRIORITY: dict[Severity, int] = {
    "info": 0,
    "notice": 1,
    "warning": 2,
    "critical": 3,
}


class FactEvidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    label: str = Field(min_length=1)
    value: str | float | int | bool | None = None
    metric: str | None = None
    unit: str | None = None
    source: str | None = None


class BaseFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    severity: Severity = "info"
    evidence: list[FactEvidence] = Field(default_factory=list)
    related_ids: list[str] = Field(default_factory=list)
    t: float = Field(ge=0)


class TrendFact(BaseFact):
    kind: Literal["trend"] = "trend"


class MilestoneFact(BaseFact):
    kind: Literal["milestone"] = "milestone"


class AnomalyFact(BaseFact):
    kind: Literal["anomaly"] = "anomaly"


class HotspotFact(BaseFact):
    kind: Literal["hotspot"] = "hotspot"


class SelectionFact(BaseFact):
    kind: Literal["selection"] = "selection"


ExplanationFact = Annotated[
    TrendFact | MilestoneFact | AnomalyFact | HotspotFact | SelectionFact,
    Field(discriminator="kind"),
]
ExplanationFactAdapter: TypeAdapter[ExplanationFact] = TypeAdapter(ExplanationFact)


class ExplanationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    severity: Severity = "info"
    evidence: list[FactEvidence] = Field(default_factory=list)
    fact_count: int = Field(default=0, ge=0)


class ExplanationPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    solver_id: str = Field(min_length=1)
    scope: ExplanationScope
    t: float = Field(ge=0)
    tick: int = Field(ge=0)
    frame_id: str | None = None
    selection_id: str | None = None
    facts: list[ExplanationFact] = Field(default_factory=list)
    summary: ExplanationSummary | None = None

    @model_validator(mode="after")
    def validate_scope_requirements(self) -> ExplanationPacket:
        if not self.facts:
            raise ValueError("explanation packets must contain at least one fact")
        if self.scope == "frame" and not self.frame_id:
            raise ValueError("frame explanation packets require frame_id")
        if self.scope == "selection" and not self.selection_id:
            raise ValueError("selection explanation packets require selection_id")
        return self


def validate_explanation_packet(packet: dict[str, Any]) -> ExplanationPacket:
    return ExplanationPacket.model_validate(packet)


def summarize_explanation_packet(packet: ExplanationPacket) -> ExplanationSummary:
    ordered = sorted(
        packet.facts,
        key=lambda fact: (
            -SEVERITY_PRIORITY[fact.severity],
            -fact.t,
            fact.title.lower(),
        ),
    )
    top = ordered[0]
    counts: dict[Severity, int] = {severity: 0 for severity in SEVERITY_PRIORITY}
    for fact in ordered:
        counts[fact.severity] += 1
    count_parts = [f"{count} {severity}" for severity, count in counts.items() if count]
    if len(ordered) == 1:
        summary_text = top.summary
    else:
        summary_text = (
            f"{len(ordered)} findings ({', '.join(count_parts)}). "
            f"Highest priority: {top.summary}"
        )
    return ExplanationSummary(
        title=top.title if len(ordered) == 1 else f"{top.title} (+{len(ordered) - 1} more)",
        summary=summary_text,
        severity=top.severity,
        evidence=top.evidence,
        fact_count=len(ordered),
    )


__all__ = [
    "AnomalyFact",
    "BaseFact",
    "ExplanationFact",
    "ExplanationPacket",
    "ExplanationScope",
    "ExplanationSummary",
    "FactEvidence",
    "HotspotFact",
    "MilestoneFact",
    "SelectionFact",
    "Severity",
    "TrendFact",
    "summarize_explanation_packet",
    "validate_explanation_packet",
]
