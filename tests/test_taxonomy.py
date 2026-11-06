from taskbench.schema import BenchmarkTask, ResultRow
from taskbench.taxonomy import (
    BASELINE,
    FAULT_GIVE_UP,
    GAVE_UP,
    IGNORED,
    NO_TOOL,
    NOT_CALLED,
    SCORER,
    TYPED,
    UNANSWERABLE,
    WRONG_RETRIEVAL,
    categorise,
    classify,
)
from tests.conftest import task_rows


def task(**kw):
    row = dict(task_rows()[0])
    row.update(kw)
    return BenchmarkTask.model_validate(row)


def row(**kw):
    base = {
        "run_id": "r",
        "config": "agent",
        "model": "m",
        "task_id": "Q0001",
        "split": "heldout",
        "kind": "single_hop",
        "epoch": 1,
        "status": "success",
        "success": False,
        "answer": "wrong",
    }
    base.update(kw)
    return ResultRow(**base)


def test_rules_in_priority_order():
    t = task()
    assert classify(row(status="error"), t) == GAVE_UP
    assert classify(row(text_tool_call=True), t) == TYPED
    assert classify(row(config="baseline"), t) == BASELINE
    assert classify(row(retrieval_recall=0.0), t) == WRONG_RETRIEVAL
    assert classify(row(retrieval_recall=1.0), t) == IGNORED


def test_unanswerable_split_between_scorer_miss_and_invented_answer():
    t = task(kind="unanswerable", supporting_passages=[], answer_keywords=[], reference_answer="I don't know")
    miss = row(kind="unanswerable", answer="This is not explicitly mentioned in the documentation.")
    invented = row(kind="unanswerable", answer="It retains logs for 30 days.")
    assert classify(miss, t) == SCORER
    assert classify(invented, t) == UNANSWERABLE


def test_ticket_tasks_need_tools():
    t = task(kind="tool", supporting_passages=[], required_tools=["lookup_ticket"], ticket_ids=["TCK-1001"])
    assert classify(row(kind="tool", config="rag"), t) == NO_TOOL
    assert classify(row(kind="tool", required_tools_called=False), t) == NOT_CALLED


def test_categorise_picks_failed_main_rows_of_one_epoch():
    rows = [row(), row(success=True), row(epoch=2), row(condition="injection", injection_exposed=False)]
    tasks = {"Q0001": task()}
    grouped = categorise(rows, tasks, epoch=1)
    assert len(grouped["agent"]) == 1


def test_giving_up_after_a_tool_timeout_is_its_own_category():
    t = task(kind="tool", supporting_passages=[], required_tools=["lookup_ticket"], ticket_ids=["TCK-1001"])
    gave_up = row(
        kind="tool",
        injected_faults=1,
        answer="I couldn't retrieve the status right now. Let's try again later.",
    )
    assert classify(gave_up, t) == FAULT_GIVE_UP
    # without an injected fault the same wording is not blamed on a timeout
    assert classify(row(kind="tool", answer="Let's try again later."), t) != FAULT_GIVE_UP
    unans = task(
        kind="unanswerable", supporting_passages=[], answer_keywords=[], reference_answer="I don't know"
    )
    timeout = row(
        kind="unanswerable", injected_faults=2, answer="Unable to retrieve the ticket due to timeouts."
    )
    assert classify(timeout, unans) == FAULT_GIVE_UP
