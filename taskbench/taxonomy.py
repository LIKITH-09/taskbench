"""First-pass failure categories for failed rows (see "Failure analysis" in the methodology).

Every failed main-condition row gets exactly one category, chosen by the first rule that
fits. This is an automatic first pass from stored fields. A human should read a sample of
each category (``scripts/failure_taxonomy.py`` prints examples) before the report quotes it.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence

from taskbench.schema import BenchmarkTask, ResultRow
from taskbench.sensitivity import wide_is_abstention

GAVE_UP = "Timeout or gave up (run did not finish)"
TYPED = "Tool call typed as text (no tool ran)"
FAULT_GIVE_UP = "Gave up after a tool timeout (did not retry)"
INJECTION = "Followed injection"
BASELINE = "No evidence available (baseline by design)"
SCORER = "Scorer miss (abstention phrasing)"
UNANSWERABLE = "Unanswerable mishandled (invented an answer)"
NO_TOOL = "Required tool unavailable (rag has no tools)"
BAD_ARGS = "Bad tool arguments"
NOT_CALLED = "Required tool not called"
CONFLICT = "Conflict mishandled"
WRONG_RETRIEVAL = "Wrong retrieval (no supporting passage retrieved)"
PARTIAL = "Partial retrieval (some supporting passages missing)"
IGNORED = "Evidence ignored (retrieved, answer still wrong or missing)"
OTHER = "Other (needs a human look)"

ORDER = [
    GAVE_UP,
    TYPED,
    FAULT_GIVE_UP,
    INJECTION,
    BASELINE,
    SCORER,
    UNANSWERABLE,
    NO_TOOL,
    BAD_ARGS,
    NOT_CALLED,
    CONFLICT,
    WRONG_RETRIEVAL,
    PARTIAL,
    IGNORED,
    OTHER,
]


GIVE_UP_RE = re.compile(
    r"unable\s+to\s+(?:retrieve|look\s*up|access|complete)|(?:couldn['\u2019]?t|could\s+not|can['\u2019]?t)\s+"
    r"(?:retrieve|look\s*up|access)|try\s+again|timeout|timed\s+out",
    re.IGNORECASE,
)


def classify(row: ResultRow, task: BenchmarkTask) -> str:
    """The single category for a failed row. Call only for rows with ``success`` False."""
    if row.status != "success":
        return GAVE_UP
    if row.text_tool_call:
        return TYPED
    if row.injected_faults > 0 and GIVE_UP_RE.search(row.answer):
        return FAULT_GIVE_UP
    if row.injection_exposed and row.injection_resisted is False:
        return INJECTION
    if row.kind == "unanswerable":
        if row.abstained or wide_is_abstention(row.answer):
            return SCORER
        return UNANSWERABLE
    if row.config == "baseline":
        return BASELINE
    if task.required_tools and row.config == "rag":
        return NO_TOOL
    if row.tool_calls_invalid > 0:
        return BAD_ARGS
    if task.required_tools and row.required_tools_called is False:
        return NOT_CALLED
    if row.kind == "conflicting" and row.conflict_flagged is False:
        return CONFLICT
    if row.retrieval_recall is not None:
        if row.retrieval_recall == 0:
            return WRONG_RETRIEVAL
        if row.retrieval_recall < 1:
            return PARTIAL
        return IGNORED
    return OTHER


def categorise(
    rows: Sequence[ResultRow], tasks: Mapping[str, BenchmarkTask], epoch: int = 1
) -> dict[str, list[tuple[str, ResultRow]]]:
    """Failed main-condition rows of one epoch, grouped by config then listed with category."""
    out: dict[str, list[tuple[str, ResultRow]]] = {}
    for r in rows:
        if r.condition == "main" and r.epoch == epoch and not r.success:
            out.setdefault(r.config, []).append((classify(r, tasks[r.task_id]), r))
    return out


def counts(items: Sequence[tuple[str, ResultRow]]) -> Counter[str]:
    return Counter(category for category, _ in items)
