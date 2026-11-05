"""Checks on the real, committed dataset, plus the validator on a miniature one."""

from collections import Counter
from pathlib import Path

import pytest

from taskbench.config import load_config
from taskbench.corpus import load_passages
from taskbench.dataset import load_corpus, load_tasks, select_tasks, validate_dataset
from taskbench.metrics import all_keywords_present
from taskbench.schema import BenchmarkTask
from tests.conftest import REPO_ROOT, write_jsonl

CFG = load_config(REPO_ROOT / "configs" / "benchmark.yaml")
TASKS = load_tasks(REPO_ROOT / CFG.dataset.tasks_path)


def test_real_dataset_has_no_problems():
    assert validate_dataset(CFG, REPO_ROOT) == []


def test_counts_match_config():
    assert Counter(t.split for t in TASKS) == {
        "dev": CFG.dataset.dev_count,
        "heldout": CFG.dataset.heldout_count,
    }
    assert dict(Counter(t.kind for t in TASKS)) == CFG.dataset.kind_counts


def test_every_kind_appears_in_both_splits():
    for kind in CFG.dataset.kind_counts:
        splits = {t.split for t in TASKS if t.kind == kind}
        assert splits == {"dev", "heldout"}, kind


def test_injection_tasks_are_heldout_single_hop():
    inj = [t for t in TASKS if t.prompt_injection]
    assert len(inj) == CFG.dataset.injection_task_count
    assert all(t.split == "heldout" and t.kind == "single_hop" for t in inj)


def test_multi_hop_doc_tasks_need_two_passages():
    passages = {p.id: p for p in load_passages(REPO_ROOT / CFG.dataset.passages_path)}
    for t in TASKS:
        if t.kind == "multi_hop" and len(t.supporting_passages) > 1:
            for pid in t.supporting_passages:
                assert not all_keywords_present(t.answer_keywords, passages[pid].text), (t.id, pid)


def test_injection_passages_only_in_injection_corpus():
    main = {p.id for p in load_corpus(CFG, REPO_ROOT, "main")}
    inj = {p.id for p in load_corpus(CFG, REPO_ROOT, "injection")}
    assert not any(pid.startswith("X") for pid in main)
    assert {pid for pid in inj if pid.startswith("X")}


def test_select_tasks():
    assert len(select_tasks(TASKS, "heldout", "injection")) == CFG.dataset.injection_task_count
    assert all(t.split == "dev" for t in select_tasks(TASKS, "dev"))


def test_validator_catches_problems(mini_root: Path, mini_cfg):
    assert validate_dataset(mini_cfg, mini_root) == []
    rows = [line for line in (mini_root / "data" / "tasks.jsonl").read_text().splitlines()]
    import json

    bad = [json.loads(r) for r in rows]
    bad[0]["supporting_passages"] = ["P0999"]
    bad[5]["ticket_ids"] = ["TCK-4040"]
    write_jsonl(mini_root / "data" / "tasks.jsonl", bad)
    problems = validate_dataset(mini_cfg, mini_root)
    assert any("P0999" in p for p in problems)
    assert any("TCK-4040" in p for p in problems)


def test_duplicate_task_ids_rejected(mini_root: Path):
    path = mini_root / "data" / "tasks.jsonl"
    first = path.read_text().splitlines()[0]
    path.write_text(path.read_text() + first + "\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_tasks(path)


def _passage(pid, text, path="a.md", origin="docs"):
    from taskbench.schema import Passage

    return Passage(id=pid, source_path=path, heading="h", text=text, license="MIT", origin=origin)


def test_extra_support_widens_citations_but_skips_injection_and_unanswerable():
    from taskbench.dataset import extra_support
    from tests.conftest import task_rows

    row = dict(task_rows()[0])
    row.update(kind="single_hop", answer_keywords=["alpha"], supporting_passages=["P0001"])
    task = BenchmarkTask.model_validate(row)
    corpus = [
        _passage("P0001", "alpha is here"),
        _passage("P0002", "also alpha here", path="b.md"),
        _passage("P0003", "nothing"),
        _passage("X0001", "alpha injected", origin="injection"),
    ]
    assert extra_support(task, corpus) == ["P0002"]
    assert extra_support(task.model_copy(update={"kind": "unanswerable"}), corpus) == []


def test_extra_support_generic_keyword_falls_back_to_same_page():
    from taskbench.dataset import MAX_ANY_PAGE_SUPPORT, extra_support
    from tests.conftest import task_rows

    row = dict(task_rows()[0])
    row.update(kind="single_hop", answer_keywords=["three"], supporting_passages=["P0001"])
    task = BenchmarkTask.model_validate(row)
    corpus = [_passage("P0001", "three", path="a.md"), _passage("P0002", "three", path="a.md")]
    corpus += [_passage(f"P1{i:03d}", "three", path="z.md") for i in range(MAX_ANY_PAGE_SUPPORT + 1)]
    assert extra_support(task, corpus) == ["P0002"]
