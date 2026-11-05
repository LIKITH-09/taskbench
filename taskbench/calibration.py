"""Calibrate automatic scorers against blind human labels.

Workflow:
1. ``taskbench label-sheet --run-id R`` writes a blind sheet: question, reference
   answer and model answer, with no automatic scores shown.
2. You fill in ``label`` (correct / incorrect) for each row and save it as
   data/human_labels.jsonl.
3. ``taskbench calibrate --run-id R`` reports agreement and Cohen's kappa between
   your labels, the deterministic scorer and (if used) the LLM judge.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from taskbench.schema import BenchmarkTask, HumanLabel, ResultRow


def cohen_kappa(a: Sequence[bool], b: Sequence[bool]) -> float | None:
    """Cohen's kappa for two binary raters; None if undefined (no items or no variation)."""
    if len(a) != len(b):
        raise ValueError("raters must label the same items")
    n = len(a)
    if n == 0:
        return None
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def agreement(a: Sequence[bool], b: Sequence[bool]) -> float | None:
    """Share of items where two raters agree."""
    if len(a) != len(b):
        raise ValueError("raters must label the same items")
    return None if not a else sum(1 for x, y in zip(a, b, strict=True) if x == y) / len(a)


def label_sheet(
    rows: Sequence[ResultRow], tasks: dict[str, BenchmarkTask], n: int = 50, seed: int = 0
) -> list[dict[str, object]]:
    """Pick ``n`` main-condition rows, spread across configurations, for blind labelling.

    Rows are stratified by configuration and by the automatic outcome so the sheet
    contains both passes and failures, but the outcome is not written to the sheet.
    """
    rnd = random.Random(seed)
    pool = [r for r in rows if r.condition == "main" and r.status == "success"]
    strata: dict[tuple[str, bool], list[ResultRow]] = {}
    for r in pool:
        strata.setdefault((r.config, r.success), []).append(r)
    for group in strata.values():
        rnd.shuffle(group)
    picked: list[ResultRow] = []
    keys = sorted(strata)
    while len(picked) < n and any(strata[k] for k in keys):
        for k in keys:
            if strata[k] and len(picked) < n:
                picked.append(strata[k].pop())
    rnd.shuffle(picked)
    return [
        {
            "run_id": r.run_id,
            "config": r.config,
            "task_id": r.task_id,
            "epoch": r.epoch,
            "question": tasks[r.task_id].question,
            "reference_answer": tasks[r.task_id].reference_answer,
            "answer": r.answer,
            "label": "",
            "labeler": "",
            "notes": "",
        }
        for r in picked
    ]


@dataclass(frozen=True)
class Calibration:
    """Agreement of each automatic scorer with the human labels."""

    n_labels: int
    n_matched: int
    deterministic_agreement: float | None
    deterministic_kappa: float | None
    judge_n: int
    judge_agreement: float | None
    judge_kappa: float | None
    disagreements: list[str]


def calibrate(labels: Sequence[HumanLabel], rows: Sequence[ResultRow]) -> Calibration:
    """Match labels to rows by (run, config, task, epoch) and compute agreement."""
    by_key = {(r.run_id, r.config, r.task_id, r.epoch): r for r in rows if r.condition == "main"}
    human: list[bool] = []
    det: list[bool] = []
    judge_h: list[bool] = []
    judge: list[bool] = []
    disagreements: list[str] = []
    for lab in labels:
        row = by_key.get((lab.run_id, lab.config, lab.task_id, lab.epoch))
        if row is None:
            continue
        h = lab.label == "correct"
        human.append(h)
        det.append(row.success)
        if h != row.success:
            disagreements.append(
                f"{lab.config}/{lab.task_id}/e{lab.epoch}: human={lab.label}, "
                f"deterministic={'correct' if row.success else 'incorrect'}"
            )
        if row.judged_success is not None:
            judge_h.append(h)
            judge.append(row.judged_success)
    return Calibration(
        n_labels=len(labels),
        n_matched=len(human),
        deterministic_agreement=agreement(human, det),
        deterministic_kappa=cohen_kappa(human, det),
        judge_n=len(judge),
        judge_agreement=agreement(judge_h, judge),
        judge_kappa=cohen_kappa(judge_h, judge),
        disagreements=disagreements,
    )
