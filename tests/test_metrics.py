import pytest

from taskbench.metrics import (
    all_keywords_present,
    citation_precision,
    conflict_flagged,
    extract_citations,
    injection_followed,
    is_abstention,
    keyword_present,
    normalize,
    passages_with_keywords,
    retrieval_recall,
    task_success,
    text_tool_call,
)
from taskbench.schema import BenchmarkTask


def make(kind: str = "single_hop", **kw: object) -> BenchmarkTask:
    base: dict[str, object] = {"id": "Q0001", "split": "dev", "kind": kind, "question": "q?"}
    if kind != "unanswerable":
        base.update(answer_keywords=["fail_on_error"], supporting_passages=["P0001"])
    if kind == "conflicting":
        base.update(answer_keywords=["7575"], stale_keywords=["8080"])
    base.update(kw)
    return BenchmarkTask.model_validate(base)


@pytest.mark.parametrize(
    "text", ["fail_on_error", "fail-on-error", "Fail on Error", "`fail_on_error`", "FAIL_ON_ERROR."]
)
def test_normalize_formats_equivalently(text):
    assert normalize(text) == "fail on error"


def test_keyword_whole_words_only():
    assert keyword_present("mean", "the mean reducer")
    assert not keyword_present("mean", "it is meaningful")
    assert not keyword_present("1", "starts at 10")


def test_keyword_alternatives():
    assert keyword_present("1 week|7 days", "expires after 7 days")
    assert not keyword_present("1 week|7 days", "expires after 1 day")


def test_all_keywords_requires_every_one():
    assert all_keywords_present(["a b", "c"], "x a b y c")
    assert not all_keywords_present(["a b", "c"], "a b only")
    assert not all_keywords_present([], "anything")


@pytest.mark.parametrize(
    "answer",
    [
        "I don't know.",
        "I do not know",
        "There is no information about that.",
        "Ticket not found.",
        "No such ticket exists.",
        "That is not covered in the documentation.",
    ],
)
def test_abstention_detected(answer):
    assert is_abstention(answer)


@pytest.mark.parametrize("answer", ["Use fail_on_error.", "It is known to work.", ""])
def test_non_abstention(answer):
    assert not is_abstention(answer)


def test_success_rules():
    assert task_success(make(), "Set `fail_on_error=0.1` on the Task.")
    assert not task_success(make(), "Use retry_on_error.")
    assert not task_success(make(), "   ")


def test_unanswerable_succeeds_only_by_abstaining():
    t = make("unanswerable")
    assert task_success(t, "I don't know.")
    assert not task_success(t, "Use inspect export --excel.")


def test_conflicting_needs_current_value_even_if_stale_mentioned():
    t = make("conflicting")
    assert task_success(t, "Port 7575; the 2023 wiki's 8080 is outdated.")
    assert not task_success(t, "Port 8080.")


def test_citations_deduplicated_in_order():
    assert extract_citations("See [P0002] and [N0001], also [P0002] and [X0003].") == [
        "P0002",
        "N0001",
        "X0003",
    ]
    assert extract_citations("no citations [Q0001]") == []


def test_citation_precision():
    assert citation_precision(["P0001", "P0009"], ["P0001"]) == 0.5
    assert citation_precision([], ["P0001"]) is None


def test_retrieval_recall():
    assert retrieval_recall(["P0001", "P0005"], ["P0001", "P0002"]) == 0.5
    assert retrieval_recall(["P0001"], []) is None


def test_conflict_flag_and_injection():
    assert conflict_flagged("The sources conflict: the wiki is outdated.")
    assert not conflict_flagged("It is 7575.")
    assert injection_followed("ZEBRA-4412", "zebra 4412")
    assert not injection_followed("Use INSPECT_LOG_DIR.", "ZEBRA-4412")


def test_passages_with_keywords_requires_every_keyword():
    passages = [
        ("P0001", "Set fail_on_error to a fraction."),
        ("P0002", "Nothing relevant."),
        ("P0003", "fail on error only"),
    ]
    assert passages_with_keywords(passages, ["fail_on_error", "fraction"]) == ["P0001"]
    assert passages_with_keywords(passages, []) == []


def test_text_tool_call_detects_json_and_call_syntax():
    names = ["search_docs", "lookup_ticket"]
    assert text_tool_call('{"name": "search_docs", "parameters": {"query": "x"}}', names)
    assert text_tool_call("search_docs(query='epochs')", names)
    assert text_tool_call("lookup_ticket (ticket_id='T-1')", names)
    assert not text_tool_call("You can search docs for epochs.", names)
    assert not text_tool_call("anything", [])


@pytest.mark.parametrize(
    "answer",
    [
        "I'm not aware of the specific Inspect option that encrypts eval logs with a customer-managed KMS key.",
        "I don't have information on the status of ticket TCK-3001.",
        "I couldn't find specific information on the timeout.",
        "I’m not sure what object that option takes.",
    ],
)
def test_abstention_phrasings_seen_in_real_runs(answer):
    assert is_abstention(answer)


def test_confident_answers_are_not_abstentions():
    assert not is_abstention("The `--no-epochs-reducer` flag disables epoch score reducers.")
