import pytest
from pydantic import ValidationError

from taskbench.schema import BenchmarkTask, HumanLabel, Passage, ResultRow, Ticket
from tests.conftest import make_row


def task(**kw: object) -> BenchmarkTask:
    base: dict[str, object] = {
        "id": "Q0001",
        "split": "dev",
        "kind": "single_hop",
        "question": "What does it control?",
        "answer_keywords": ["timeout"],
        "supporting_passages": ["P0001"],
    }
    base.update(kw)
    return BenchmarkTask.model_validate(base)


def test_valid_task():
    t = task()
    assert t.prompt_injection is False
    assert t.review_status == "draft"


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError, match="answer_keyword"):
        task(answer_keyword=["typo"])


def test_empty_question_rejected():
    with pytest.raises(ValidationError):
        task(question="")


def test_bad_id_rejected():
    with pytest.raises(ValidationError):
        task(id="TB-0001")


def test_unanswerable_cannot_have_keywords():
    with pytest.raises(ValidationError, match="unanswerable"):
        task(kind="unanswerable", supporting_passages=[])


def test_answerable_needs_keywords():
    with pytest.raises(ValidationError, match="answer_keywords"):
        task(answer_keywords=[])


def test_single_hop_needs_supporting_passages():
    with pytest.raises(ValidationError, match="supporting_passages"):
        task(supporting_passages=[])


def test_tool_task_requires_lookup_ticket_and_ids():
    with pytest.raises(ValidationError, match="lookup_ticket"):
        task(kind="tool", supporting_passages=[])
    with pytest.raises(ValidationError, match="ticket_ids"):
        task(kind="tool", supporting_passages=[], required_tools=["lookup_ticket"])
    ok = task(kind="tool", supporting_passages=[], required_tools=["lookup_ticket"], ticket_ids=["TCK-1001"])
    assert ok.kind == "tool"


def test_unknown_tool_name_rejected():
    with pytest.raises(ValidationError):
        task(required_tools=["web_search"])


def test_conflicting_needs_stale_keywords():
    with pytest.raises(ValidationError, match="stale_keywords"):
        task(kind="conflicting")


def test_injection_must_be_heldout_with_marker():
    with pytest.raises(ValidationError, match="held out"):
        task(prompt_injection=True, injection_marker="Z-1")
    with pytest.raises(ValidationError, match="injection_marker"):
        task(split="heldout", prompt_injection=True)
    with pytest.raises(ValidationError, match="non-injection"):
        task(injection_marker="Z-1")
    assert task(split="heldout", prompt_injection=True, injection_marker="Z-1").prompt_injection


def test_result_row_keeps_missing_usage_as_null():
    row = make_row(status="error", success=False, error_type="timeout")
    assert row.input_tokens is None
    assert row.estimated_cost_usd is None


def test_failed_execution_cannot_be_success():
    with pytest.raises(ValidationError, match="failed execution"):
        make_row(status="error", success=True)


def test_status_is_a_closed_set():
    with pytest.raises(ValidationError):
        make_row(status="anything goes")


def test_injection_resisted_requires_exposure():
    with pytest.raises(ValidationError, match="injection_exposed"):
        make_row(injection_resisted=True)
    assert make_row(injection_exposed=True, injection_resisted=True).injection_resisted


def test_recovered_requires_fault():
    with pytest.raises(ValidationError, match="fault"):
        make_row(recovered=True)


def test_tool_error_counts_bounded():
    with pytest.raises(ValidationError, match="exceed"):
        make_row(tool_calls=1, tool_errors=2)


def test_result_row_rejects_unknown_field():
    with pytest.raises(ValidationError):
        ResultRow.model_validate({**make_row().model_dump(), "succes": True})


def test_passage_ticket_label_models():
    Passage(id="N0001", source_path="x", heading="h", text="t", license="CC0", origin="internal_note")
    with pytest.raises(ValidationError):
        Passage(id="Q0001", source_path="x", heading="h", text="t", license="MIT")
    with pytest.raises(ValidationError):
        Ticket(
            id="TCK-1",
            title="t",
            status="open",
            component="c",
            priority="low",
            owner="o",
            opened="2026-01-01",
        )
    with pytest.raises(ValidationError):
        HumanLabel(run_id="r", config="rag", task_id="Q0001", epoch=1, label="maybe", labeler="me")
