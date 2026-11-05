"""Tool logic that does not need Inspect: the ticket database and fault decisions.

The Inspect tool wrappers themselves are exercised end to end in test_smoke.py.
"""

import os
import time
from pathlib import Path

import pytest

from taskbench.faults import fault_fires
from taskbench.make_tickets import build_db, ensure_db, get_ticket, load_tickets


def test_build_and_lookup(mini_root: Path):
    tickets = load_tickets(mini_root / "data" / "tickets.jsonl")
    db = mini_root / "data" / "tickets.sqlite"
    build_db(tickets, db)
    t = get_ticket(db, "TCK-1001")
    assert t is not None and t.owner == "Priya"
    assert get_ticket(db, "  tck-1002 ") is not None
    assert get_ticket(db, "TCK-9999") is None


def test_lookup_is_read_only(mini_root: Path):
    db = mini_root / "data" / "tickets.sqlite"
    build_db(load_tickets(mini_root / "data" / "tickets.jsonl"), db)
    assert get_ticket(db, "TCK-1001'; DROP TABLE tickets; --") is None
    assert get_ticket(db, "TCK-1001") is not None


def test_ensure_db_rebuilds_when_source_changes(mini_root: Path):
    src = mini_root / "data" / "tickets.jsonl"
    db = mini_root / "data" / "tickets.sqlite"
    ensure_db(src, db)
    old = db.stat().st_mtime
    time.sleep(0.01)
    src.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    os.utime(src, (old + 10, old + 10))
    ensure_db(src, db)
    assert db.stat().st_mtime > old


def test_duplicate_ticket_ids_rejected(tmp_path: Path, mini_root: Path):
    src = mini_root / "data" / "tickets.jsonl"
    dup = tmp_path / "dup.jsonl"
    line = src.read_text(encoding="utf-8").splitlines()[0]
    dup.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_tickets(dup)


def test_fault_fires_is_deterministic_and_calibrated():
    assert fault_fires(1, "Q0001:1", 0, 0.0) is False
    assert fault_fires(1, "Q0001:1", 0, 1.0) is True
    assert fault_fires(7, "Q0001:1", 3, 0.5) == fault_fires(7, "Q0001:1", 3, 0.5)
    hits = sum(fault_fires(42, f"Q{i:04d}:1", 0, 0.10) for i in range(5000))
    assert 400 < hits < 600  # about 10%


def test_fault_depends_on_epoch():
    decisions = {fault_fires(3, f"Q0001:{epoch}", 0, 0.5) for epoch in range(1, 40)}
    assert decisions == {True, False}


def test_agent_prompt_requires_search_before_giving_up():
    pytest.importorskip("inspect_ai")
    from taskbench.solvers import AGENT_PROMPT

    assert "at least once" in AGENT_PROMPT and "search_docs" in AGENT_PROMPT
    assert "never pass one to lookup_ticket" in AGENT_PROMPT
