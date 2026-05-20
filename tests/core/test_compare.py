from __future__ import annotations

from persephone.compare import compare_metric_records


def test_compare_metric_records_aligns_missing_time_points_and_summarizes() -> None:
    result = compare_metric_records(
        run_a="run-a",
        run_b="run-b",
        metric="infected_count",
        records_a=[
            {"t": 0, "metric": "infected_count", "value": 1},
            {"t": 2, "metric": "infected_count", "value": 5},
        ],
        records_b=[
            {"t": 1, "metric": "infected_count", "value": 3},
            {"t": 2, "metric": "infected_count", "value": 4},
        ],
    )

    assert result.aligned == [
        {"t": 0.0, "run_a": 1.0, "run_b": None},
        {"t": 1.0, "run_a": None, "run_b": 3.0},
        {"t": 2.0, "run_a": 5.0, "run_b": 4.0},
    ]
    assert result.summaries["run-a"].peak == 5.0
    assert result.summaries["run-a"].final == 5.0
    assert result.summaries["run-a"].auc == 6.0
    assert result.summaries["run-b"].peak == 4.0
    assert result.summaries["run-b"].final == 4.0
    assert result.summaries["run-b"].auc == 3.5
