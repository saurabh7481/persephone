from __future__ import annotations

from typing import Any

from persephone.config.models import ExperimentConfig
from persephone.core.explanations import ExplanationPacket, ExplanationSummary, TrendFact
from persephone.core.frames import FieldFrame, FrameIndex, FramePayloadRef, GraphFrame
from persephone.core.records import EventRecord, MetricRecord, RunManifest, SchedulerTelemetry


def experiment_config_json_schema() -> dict[str, Any]:
    """Return the JSON Schema for Persephone experiment configs."""
    return ExperimentConfig.model_json_schema()


def core_record_json_schemas() -> dict[str, dict[str, Any]]:
    """Return JSON Schemas for core persisted record types."""
    return {
        "MetricRecord": MetricRecord.model_json_schema(),
        "EventRecord": EventRecord.model_json_schema(),
        "SchedulerTelemetry": SchedulerTelemetry.model_json_schema(),
        "RunManifest": RunManifest.model_json_schema(),
        "FieldFrame": FieldFrame.model_json_schema(),
        "GraphFrame": GraphFrame.model_json_schema(),
        "FrameIndex": FrameIndex.model_json_schema(),
        "FramePayloadRef": FramePayloadRef.model_json_schema(),
        "ExplanationPacket": ExplanationPacket.model_json_schema(),
        "ExplanationSummary": ExplanationSummary.model_json_schema(),
        "TrendFact": TrendFact.model_json_schema(),
    }
