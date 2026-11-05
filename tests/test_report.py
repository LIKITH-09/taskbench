"""report.py must turn every sample, including failures, into exactly one valid row."""

import pytest

from taskbench.config import ModelPrice
from taskbench.report import parse_task_name, row_from_sample, rows_from_samples
from tests.conftest import task_rows

TASK = task_rows()[0]
PRICE = ModelPrice(
    input_usd_per_million=1.0,
    output_usd_per_million=2.0,
    source_url="https://example.com",
    checked_on="2026-10-22",
)


def sample(**kw):
    base = {
        "id": TASK["id"],
        "epoch": 1,
        "metadata": {"task": TASK},
        "scores": {
            "taskbench_scorer": {
                "value": "C",
                "answer": "Use INSPECT_LOG_DIR [P0001].",
                "metadata": {
                    "abstained": False,
                    "cited_count": 1,
                    "citation_precision": 1.0,
                    "retrieval_recall": 1.0,
                },
            }
        },
        "error": None,
        "limit": None,
        "total_time": 2.5,
        "model_usage": {"mockllm/model": {"input_tokens": 1000, "output_tokens": 500}},
        "output": {"completion": "Use INSPECT_LOG_DIR [P0001]."},
    }
    base.update(kw)
    return base


def build(s, config="rag", condition="main"):
    return row_from_sample(
        s, run_id="r1", config=config, condition=condition, model="mockllm/model", price=PRICE
    )


def test_parse_task_name():
    assert parse_task_name("taskbench_agent_faults_main") == ("agent_faults", "main")
    assert parse_task_name("taskbench_rag_injection") == ("rag", "injection")
    with pytest.raises(ValueError):
        parse_task_name("other_task")
    with pytest.raises(ValueError):
        parse_task_name("taskbench_unknown_main")


def test_successful_sample():
    row = build(sample())
    assert row.status == "success" and row.success
    assert (row.input_tokens, row.output_tokens) == (1000, 500)
    assert row.estimated_cost_usd == pytest.approx(0.002)
    assert row.latency_s == 2.5 and row.citation_precision == 1.0


def test_incorrect_sample():
    s = sample()
    s["scores"]["taskbench_scorer"]["value"] = "I"
    row = build(s)
    assert row.status == "success" and not row.success


def test_errored_sample_is_kept_as_failure():
    row = build(sample(error={"message": "connection reset", "traceback": "..."}, scores=None))
    assert row.status == "error" and not row.success
    assert row.error_type == "connection reset"


def test_limit_sample_is_failure_even_if_scored_correct():
    row = build(sample(limit={"type": "message", "limit": 12}))
    assert row.status == "limit_reached" and not row.success
    assert row.error_type == "limit:message"


def test_unscored_sample_is_error():
    assert build(sample(scores={})).error_type == "not_scored"


def test_cached_input_tokens_are_counted():
    usage = {
        "mockllm/model": {
            "input_tokens": 166,
            "input_tokens_cache_read": 355,
            "input_tokens_cache_write": 10,
            "output_tokens": 30,
        }
    }
    row = build(sample(model_usage=usage))
    assert (row.input_tokens, row.output_tokens) == (531, 30)


def test_null_cache_fields_are_ignored():
    usage = {"mockllm/model": {"input_tokens": 100, "input_tokens_cache_read": None, "output_tokens": 5}}
    assert build(sample(model_usage=usage)).input_tokens == 100


def test_missing_usage_stays_null():
    row = build(sample(model_usage={}))
    assert row.input_tokens is None and row.estimated_cost_usd is None


def test_namespaced_scorer_names_are_found():
    s = sample()
    s["scores"] = {"taskbench/taskbench_scorer": s["scores"]["taskbench_scorer"]}
    assert build(s).success


def test_judge_score_recorded():
    s = sample()
    s["scores"]["model_graded_qa"] = {"value": "I"}
    assert build(s).judged_success is False


def test_fault_and_injection_fields():
    s = sample()
    s["scores"]["taskbench_scorer"]["metadata"].update(
        injected_faults=2, tool_calls=3, tool_errors=1, injection_exposed=True, injection_resisted=False
    )
    row = build(s, config="agent_faults")
    assert row.injected_faults == 2 and row.recovered is True
    assert row.injection_exposed and row.injection_resisted is False


def test_one_row_per_sample():
    samples = [sample(epoch=e) for e in (1, 2, 3)] + [sample(epoch=4, error={"message": "x"}, scores=None)]
    rows = rows_from_samples(
        samples, run_id="r1", task_name="taskbench_rag_main", model="mockllm/model", price=None
    )
    assert len(rows) == 4
    assert [r.status for r in rows].count("error") == 1


def test_text_tool_call_flag_is_carried():
    s = sample()
    s["scores"]["taskbench_scorer"]["metadata"]["text_tool_call"] = True
    assert build(s, config="agent").text_tool_call is True
    assert build(sample()).text_tool_call is None
