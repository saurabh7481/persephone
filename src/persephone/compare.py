from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


class MetricSummary(BaseModel):
    peak: float
    final: float
    auc: float


class CompareResult(BaseModel):
    run_a: str
    run_b: str
    metric: str
    aligned: list[dict[str, float | None]]
    summaries: dict[str, MetricSummary]


@dataclass(frozen=True)
class MetricPoint:
    t: float
    value: float


def compare_metric_records(
    *,
    run_a: str,
    run_b: str,
    metric: str,
    records_a: list[dict[str, Any]],
    records_b: list[dict[str, Any]],
) -> CompareResult:
    points_a = _metric_points(records_a, metric)
    points_b = _metric_points(records_b, metric)
    values_a = {point.t: point.value for point in points_a}
    values_b = {point.t: point.value for point in points_b}
    times = sorted({*values_a, *values_b})

    return CompareResult(
        run_a=run_a,
        run_b=run_b,
        metric=metric,
        aligned=[
            {
                "t": t,
                "run_a": values_a.get(t),
                "run_b": values_b.get(t),
            }
            for t in times
        ],
        summaries={
            run_a: summarize_metric_points(points_a),
            run_b: summarize_metric_points(points_b),
        },
    )


def summarize_metric_points(points: list[MetricPoint]) -> MetricSummary:
    if not points:
        return MetricSummary(peak=0.0, final=0.0, auc=0.0)

    ordered = sorted(points, key=lambda point: point.t)
    auc = 0.0
    for left, right in zip(ordered, ordered[1:], strict=False):
        auc += ((left.value + right.value) / 2.0) * (right.t - left.t)

    return MetricSummary(
        peak=max(point.value for point in ordered),
        final=ordered[-1].value,
        auc=auc,
    )


def _metric_points(records: list[dict[str, Any]], metric: str) -> list[MetricPoint]:
    points: list[MetricPoint] = []
    for record in records:
        if record.get("metric") != metric:
            continue
        t = record.get("t")
        value = record.get("value")
        if not isinstance(t, int | float) or not isinstance(value, int | float):
            continue
        points.append(MetricPoint(t=float(t), value=float(value)))
    return sorted(points, key=lambda point: point.t)
