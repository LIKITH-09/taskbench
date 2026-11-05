import math

import pytest

from taskbench.config import ModelPrice
from taskbench.stats import (
    Rate,
    cluster_bootstrap,
    cost_per_success,
    paired_comparison,
    percentile,
    rate,
    summarize,
    summary_markdown,
)
from tests.conftest import make_row


def test_cost_per_success():
    assert cost_per_success(2.0, 4) == pytest.approx(0.5)


def test_cost_per_success_undefined_for_zero_successes():
    assert cost_per_success(2.0, 0) is None


@pytest.mark.parametrize("bad", [(-1.0, 1), (2.0, -1), (math.nan, 3), (math.inf, 3)])
def test_cost_per_success_rejects_invalid(bad):
    with pytest.raises(ValueError):
        cost_per_success(*bad)


def test_percentile():
    assert percentile([], 50) is None
    assert percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)
    assert percentile([5.0], 95) == 5.0
    with pytest.raises(ValueError):
        percentile([1], 101)


def test_rate_formatting():
    assert Rate(3, 4).value == 0.75
    assert Rate(0, 0).value is None
    assert "3/4" in Rate(3, 4, 0.5, 1.0).fmt()


def test_cluster_bootstrap_keeps_epochs_together():
    groups = {"Q1": [1, 1, 1], "Q2": [0, 0, 0], "Q3": [1, 1, 1], "Q4": [0, 0, 0]}
    lo, hi = cluster_bootstrap(groups, n_boot=500, seed=1)
    assert 0 <= lo <= 0.5 <= hi <= 1
    assert cluster_bootstrap({"Q1": [1]}) is None


def rows_for(config: str, outcomes: dict[str, list[bool]], **extra) -> list:
    return [
        make_row(config=config, task_id=t, epoch=e + 1, success=ok, **extra)
        for t, oks in outcomes.items()
        for e, ok in enumerate(oks)
    ]


def test_rate_denominator_excludes_filtered_rows():
    rows = rows_for("rag", {"Q0001": [True, False]}) + rows_for("rag", {"Q0002": [True]})
    r = rate(rows, lambda r: r.success, include=lambda r: r.task_id == "Q0001", ci=False)
    assert (r.numerator, r.denominator) == (1, 2)


def test_summarize_core_numbers():
    rows = rows_for(
        "rag",
        {"Q0001": [True, True], "Q0002": [False, True]},
        input_tokens=100,
        output_tokens=20,
        latency_s=1.0,
        estimated_cost_usd=0.01,
        citation_precision=0.5,
        cited_count=2,
    )
    rows.append(
        make_row(
            config="rag",
            task_id="Q0003",
            status="error",
            success=False,
            error_type="boom",
            estimated_cost_usd=0.01,
            input_tokens=0,
            output_tokens=0,
        )
    )
    (s,) = summarize(rows)
    assert s.rows == 5 and s.tasks == 3
    assert (s.success.numerator, s.success.denominator) == (3, 5)
    assert s.statuses == {"success": 4, "error": 1}
    assert s.cost_per_success_usd == pytest.approx(0.05 / 3)
    assert s.citation_precision == (0.5, 4)
    assert s.latency_p99_s is None  # fewer than 200 rows


def test_cost_unknown_if_any_row_unpriced():
    rows = rows_for("rag", {"Q0001": [True]}, estimated_cost_usd=0.01)
    rows += rows_for("rag", {"Q0002": [True]})
    (s,) = summarize(rows)
    assert s.total_cost_usd is None and s.cost_per_success_usd is None


def test_reference_cost_estimate():
    price = ModelPrice(
        input_usd_per_million=1,
        output_usd_per_million=1,
        source_url="https://example.com",
        checked_on="2026-10-22",
    )
    rows = rows_for("rag", {"Q0001": [True, False]}, input_tokens=500_000, output_tokens=500_000)
    (s,) = summarize(rows, reference_price=price)
    assert s.reference_cost_per_success_usd == pytest.approx(2.0)


def test_reliability_metrics_have_correct_denominators():
    rows = [
        make_row(
            config="agent_faults",
            task_id="Q0001",
            injected_faults=1,
            recovered=True,
            tool_calls=2,
            tool_errors=1,
        ),
        make_row(
            config="agent_faults",
            task_id="Q0002",
            injected_faults=2,
            success=False,
            recovered=False,
            tool_calls=3,
            tool_calls_invalid=1,
        ),
        make_row(config="agent_faults", task_id="Q0003", tool_calls=1),
    ]
    (s,) = summarize(rows)
    assert (s.recovery.numerator, s.recovery.denominator) == (1, 2)
    assert (s.tool_validity.numerator, s.tool_validity.denominator) == (5, 6)


def test_injection_resistance_counts_only_exposed_rows():
    rows = [
        make_row(condition="injection", task_id="Q0001", injection_exposed=True, injection_resisted=True),
        make_row(condition="injection", task_id="Q0002", injection_exposed=True, injection_resisted=False),
        make_row(condition="injection", task_id="Q0003"),
    ]
    (s,) = summarize(rows)
    assert (s.injection_resistance.numerator, s.injection_resistance.denominator) == (1, 2)


def test_paired_comparison_uses_shared_tasks_only():
    rows = rows_for("rag", {"Q0001": [False, False], "Q0002": [True, True], "Q0003": [False]})
    rows += rows_for("agent", {"Q0001": [True, True], "Q0002": [True, True], "Q0009": [True]})
    c = paired_comparison(rows, "rag", "agent", n_boot=200)
    assert c.shared_tasks == 2
    assert c.diff == pytest.approx(0.5)
    assert (c.b_better, c.a_better, c.ties) == (1, 0, 1)
    assert paired_comparison(rows, "rag", "baseline").diff is None


def test_markdown_renders():
    rows = rows_for("baseline", {"Q0001": [True]}) + rows_for("rag", {"Q0001": [False]})
    md = summary_markdown(summarize(rows), [paired_comparison(rows, "baseline", "rag", n_boot=50)], "r1")
    assert "| main | baseline |" in md and "Paired comparisons" in md
