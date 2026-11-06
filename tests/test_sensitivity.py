import pytest

from taskbench.schema import ResultRow
from taskbench.sensitivity import rescore, wide_is_abstention
from tests.conftest import task_rows


@pytest.mark.parametrize(
    "answer",
    [
        "The name of Inspect's built-in vector database is not explicitly mentioned in the provided documentation.",
        "Based on the documentation, there is no specific command mentioned for creating a Jira issue.",
        "That option isn't mentioned anywhere in the docs.",
        "I don't know.",
    ],
)
def test_wide_rule_accepts_documentation_silence_as_abstention(answer):
    assert wide_is_abstention(answer)


@pytest.mark.parametrize(
    "answer",
    [
        "I don't have real-time access to the ticket system, so I can't check the status.",
        "The `--limit` option shuffles the dataset's samples.",
        "The timeout is mentioned in the docs as 5 minutes.",
        "Inspect retains logs for 30 days by default.",
    ],
)
def test_wide_rule_rejects_deflections_and_real_answers(answer):
    assert not wide_is_abstention(answer)


def _row(config, success, answer, kind="unanswerable"):
    base = {
        "run_id": "r",
        "config": config,
        "model": "m",
        "task_id": "Q0001",
        "split": "heldout",
        "kind": kind,
        "epoch": 1,
        "status": "success",
        "success": success,
        "answer": answer,
    }
    return ResultRow(**base)


def test_rescore_only_changes_unanswerable_incorrect_rows():
    rows = [
        _row("agent", False, "There is no specific command mentioned for that."),
        _row("agent", False, "It retains logs for 30 days."),
        _row("agent", True, "I don't know."),
        _row("agent", False, "not explicitly mentioned", kind="single_hop"),
    ]
    (s,) = rescore(rows)
    assert (s.unanswerable_rows, s.strict_success, s.wide_success) == (3, 1, 2)
    assert (s.total_strict, s.total_wide) == (1, 2)
    assert len(s.changed) == 1
    assert task_rows()  # fixture import sanity
