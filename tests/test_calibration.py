import pytest

from taskbench.calibration import agreement, calibrate, cohen_kappa, label_sheet
from taskbench.schema import BenchmarkTask, HumanLabel
from tests.conftest import make_row


def test_kappa_known_values():
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == pytest.approx(1.0)
    assert cohen_kappa([True, True, False, False], [False, False, True, True]) == pytest.approx(-1.0)
    # 20 items, observed agreement 0.7, both raters 50/50 -> kappa 0.4
    a = [True] * 10 + [False] * 10
    b = [True] * 7 + [False] * 3 + [True] * 3 + [False] * 7
    assert cohen_kappa(a, b) == pytest.approx(0.4)


def test_kappa_undefined_cases():
    assert cohen_kappa([], []) is None
    assert cohen_kappa([True, True], [True, True]) is None
    with pytest.raises(ValueError):
        cohen_kappa([True], [True, False])


def test_agreement():
    assert agreement([True, False], [True, True]) == 0.5
    assert agreement([], []) is None


def tasks() -> dict[str, BenchmarkTask]:
    return {
        f"Q{i:04d}": BenchmarkTask(
            id=f"Q{i:04d}",
            split="heldout",
            kind="single_hop",
            question=f"q{i}",
            answer_keywords=["x"],
            supporting_passages=["P0001"],
        )
        for i in range(1, 21)
    }


def test_label_sheet_is_blind_and_mixed():
    rows = [
        make_row(config=c, task_id=f"Q{i:04d}", success=i % 2 == 0)
        for c in ("rag", "agent")
        for i in range(1, 21)
    ]
    rows.append(make_row(config="rag", task_id="Q0001", condition="injection"))
    sheet = label_sheet(rows, tasks(), n=12, seed=3)
    assert len(sheet) == 12
    assert all("success" not in s and s["label"] == "" for s in sheet)
    assert {s["config"] for s in sheet} == {"rag", "agent"}
    keys = {(s["config"], s["task_id"]) for s in sheet}
    outcomes = {r.success for r in rows if (r.config, r.task_id) in keys and r.condition == "main"}
    assert outcomes == {True, False}


def test_calibrate_matches_and_counts():
    rows = [
        make_row(task_id="Q0001", success=True, judged_success=True),
        make_row(task_id="Q0002", success=False, judged_success=True),
        make_row(task_id="Q0003", success=True),
    ]
    labels = [
        HumanLabel(run_id="r1", config="rag", task_id=t, epoch=1, label=lab, labeler="me")
        for t, lab in [("Q0001", "correct"), ("Q0002", "correct"), ("Q0003", "correct"), ("Q0099", "correct")]
    ]
    c = calibrate(labels, rows)
    assert (c.n_labels, c.n_matched, c.judge_n) == (4, 3, 2)
    assert c.deterministic_agreement == pytest.approx(2 / 3)
    assert c.judge_agreement == 1.0
    assert len(c.disagreements) == 1 and "Q0002" in c.disagreements[0]
