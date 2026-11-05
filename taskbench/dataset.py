"""Load tasks and corpora, and check the dataset's integrity.

``validate_dataset`` is the single place where the dataset rules live. The test
suite and the ``taskbench validate`` command both call it.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from taskbench.config import BenchmarkConfig
from taskbench.corpus import load_passages
from taskbench.make_tickets import load_tickets
from taskbench.metrics import keyword_present, passages_with_keywords
from taskbench.schema import BenchmarkTask, Condition, Passage, SplitName


def load_tasks(path: Path) -> list[BenchmarkTask]:
    """Load and validate tasks; task IDs must be unique."""
    with path.open(encoding="utf-8") as f:
        tasks = [BenchmarkTask.model_validate_json(line) for line in f if line.strip()]
    ids = [t.id for t in tasks]
    dupes = [i for i, n in Counter(ids).items() if n > 1]
    if dupes:
        raise ValueError(f"duplicate task IDs: {dupes}")
    return tasks


def select_tasks(
    tasks: list[BenchmarkTask], split: SplitName, condition: Condition = "main"
) -> list[BenchmarkTask]:
    """Tasks for one split. The injection condition uses only the tagged injection tasks."""
    chosen = [t for t in tasks if t.split == split]
    if condition == "injection":
        chosen = [t for t in chosen if t.prompt_injection]
    return chosen


def load_corpus(cfg: BenchmarkConfig, root: Path, condition: Condition = "main") -> list[Passage]:
    """Documentation passages plus internal notes; injection passages only when asked."""
    ds = cfg.dataset
    corpus = load_passages(root / ds.passages_path) + load_passages(root / ds.internal_notes_path)
    if condition == "injection":
        corpus += load_passages(root / ds.injection_passages_path)
    return corpus


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_dataset(cfg: BenchmarkConfig, root: Path) -> list[str]:
    """Return a list of problems; an empty list means the dataset is consistent."""
    ds = cfg.dataset
    problems: list[str] = []
    tasks = load_tasks(root / ds.tasks_path)
    passages = {p.id: p for p in load_corpus(cfg, root, condition="injection")}
    tickets = {t.id for t in load_tickets(root / ds.tickets_path)}

    if ds.passages_sha256 and sha256_file(root / ds.passages_path) != ds.passages_sha256:
        problems.append("passages.jsonl does not match passages_sha256 in benchmark.yaml")

    splits = Counter(t.split for t in tasks)
    if splits["dev"] != ds.dev_count or splits["heldout"] != ds.heldout_count:
        problems.append(f"split counts {dict(splits)} != dev {ds.dev_count} / heldout {ds.heldout_count}")
    kinds = Counter(t.kind for t in tasks)
    if dict(kinds) != ds.kind_counts:
        problems.append(f"kind counts {dict(kinds)} != {ds.kind_counts}")
    n_injection = sum(t.prompt_injection for t in tasks)
    if n_injection != ds.injection_task_count:
        problems.append(f"{n_injection} injection tasks, expected {ds.injection_task_count}")

    markers = [t.injection_marker for t in tasks if t.injection_marker]
    if len(markers) != len(set(markers)):
        problems.append("injection markers must be unique")
    injection_text = " ".join(p.text for p in passages.values() if p.origin == "injection")
    for marker in markers:
        if marker not in injection_text:
            problems.append(f"marker {marker} does not appear in any injection passage")

    for t in tasks:
        for pid in t.supporting_passages:
            if pid not in passages:
                problems.append(f"{t.id}: supporting passage {pid} does not exist")
            elif passages[pid].origin == "injection":
                problems.append(f"{t.id}: an injection passage cannot be supporting evidence")
        support = "\n".join(passages[p].text for p in t.supporting_passages if p in passages)
        if t.kind != "tool":
            for k in t.answer_keywords:
                if not keyword_present(k, support):
                    problems.append(f"{t.id}: keyword {k!r} not found in its supporting passages")
        for tid in t.ticket_ids:
            exists = tid in tickets
            if t.kind == "unanswerable" and exists:
                problems.append(f"{t.id}: unanswerable task references existing ticket {tid}")
            if t.kind != "unanswerable" and not exists:
                problems.append(f"{t.id}: ticket {tid} does not exist")
    return problems


def write_jsonl(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


MAX_ANY_PAGE_SUPPORT = 8


def extra_support(t: BenchmarkTask, corpus: list[Passage]) -> list[str]:
    """Passages other than the listed ones that also state the answer (valid citations).

    A passage qualifies when it contains every answer keyword. Injected passages never
    qualify. If more than ``MAX_ANY_PAGE_SUPPORT`` passages match (the keyword is generic,
    such as "3"), only passages from the same source page as a listed passage are kept, so
    the list stays meaningful.
    """
    if t.kind == "unanswerable" or not t.supporting_passages:
        return []
    by_id = {p.id: p for p in corpus}
    citable = [(p.id, p.text) for p in corpus if p.origin != "injection" and not p.id.startswith("X")]
    found = [i for i in passages_with_keywords(citable, t.answer_keywords) if i not in t.supporting_passages]
    if len(found) > MAX_ANY_PAGE_SUPPORT:
        pages = {by_id[i].source_path for i in t.supporting_passages if i in by_id}
        found = [i for i in found if by_id[i].source_path in pages]
    return found
