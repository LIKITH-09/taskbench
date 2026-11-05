"""Build the fictional ticket database from ``data/tickets.jsonl``.

``tickets.jsonl`` is the committed source of truth. The SQLite file is a build
product (git-ignored), rebuilt deterministically by ``python -m taskbench.make_tickets``.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from taskbench.schema import Ticket

COLUMNS = ("id", "title", "status", "component", "priority", "owner", "opened", "note")


def load_tickets(path: Path) -> list[Ticket]:
    """Load and validate tickets from JSONL; IDs must be unique."""
    with path.open(encoding="utf-8") as f:
        tickets = [Ticket.model_validate_json(line) for line in f if line.strip()]
    ids = [t.id for t in tickets]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate ticket IDs in {path}")
    return tickets


def build_db(tickets: list[Ticket], db_path: Path) -> None:
    """(Re)create ``db_path`` holding exactly ``tickets``."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE tickets (id TEXT PRIMARY KEY, title TEXT, status TEXT, "
            "component TEXT, priority TEXT, owner TEXT, opened TEXT, note TEXT)"
        )
        conn.executemany(
            f"INSERT INTO tickets VALUES ({', '.join('?' for _ in COLUMNS)})",
            [tuple(getattr(t, c) for c in COLUMNS) for t in tickets],
        )
    conn.close()


def get_ticket(db_path: Path, ticket_id: str) -> Ticket | None:
    """Return one ticket by ID (case-insensitive, surrounding spaces ignored), or None."""
    key = ticket_id.strip().upper()
    # as_uri() handles Windows drive letters, backslashes and spaces in the path.
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        row = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM tickets WHERE id = ?", (key,)).fetchone()
    finally:
        conn.close()
    return None if row is None else Ticket(**dict(zip(COLUMNS, row, strict=True)))


def ensure_db(jsonl_path: Path, db_path: Path) -> Path:
    """Build the database if it is missing or older than its JSONL source."""
    if not db_path.exists() or db_path.stat().st_mtime < jsonl_path.stat().st_mtime:
        build_db(load_tickets(jsonl_path), db_path)
    return db_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build data/tickets.sqlite from JSONL.")
    parser.add_argument("--source", type=Path, default=Path("data/tickets.jsonl"))
    parser.add_argument("--db", type=Path, default=Path("data/tickets.sqlite"))
    args = parser.parse_args(argv)
    tickets = load_tickets(args.source)
    build_db(tickets, args.db)
    print(f"Wrote {len(tickets)} tickets to {args.db}")


if __name__ == "__main__":
    main()
