"""Interactive review of the benchmark tasks (see "Review procedure" in data/README.md).

Run from the project folder with the virtual environment active:

    python scripts/review_tasks.py --split heldout

For every task still marked ``draft`` it shows the question, the scoring keys and the
evidence, then asks what to do:

    a   accept: set review_status to "reviewed"
    f   flag: keep it as "draft" and save a note in data/review_flags.jsonl
    s   skip for now
    q   quit (everything you did so far is already saved)

Progress is saved after every decision, so you can stop at any time and run the script
again; it only shows tasks that are still drafts and not yet flagged. Only the
``review_status`` text on that task's line changes; the rest of the file is untouched.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DRAFT = '"review_status":"draft"'
REVIEWED = '"review_status":"reviewed"'
PASSAGE_CHARS = 1500


def read_lines(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as fh:
        return fh.read().splitlines(keepends=True)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in read_lines(path) if line.strip()]


def norm(text: str) -> str:
    return " " + " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split()) + " "


def keyword_in(keyword: str, text: str) -> bool:
    haystack = norm(text)
    return any(norm(alt) in haystack for alt in keyword.split("|") if alt.strip())


def mark_reviewed(path: Path, task_id: str) -> None:
    lines = read_lines(path)
    for i, line in enumerate(lines):
        if f'"id":"{task_id}"' in line.replace('"id": "', '"id":"'):
            if DRAFT not in line:
                raise SystemExit(f"{task_id}: expected {DRAFT} in tasks.jsonl, found something else")
            lines[i] = line.replace(DRAFT, REVIEWED, 1)
            break
    else:
        raise SystemExit(f"{task_id} not found in {path}")
    write_lines(path, lines)


def write_lines(path: Path, lines: list[str]) -> None:
    """Save the file safely, tolerating Windows file locks.

    Writes a temporary copy and swaps it in. If Windows refuses the swap (VS Code,
    antivirus or OneDrive briefly holding the file), retry a few times, then write
    straight into the real file instead.
    """
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)
    for _ in range(6):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            time.sleep(0.5)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)
    try:
        tmp.unlink()
    except OSError:
        pass


def show(task: dict, passages: dict[str, dict], tickets: dict[str, dict], index, position: str) -> None:
    bar = "=" * 78
    print(f"\n{bar}\n{task['id']}  [{task['kind']}, {task['split']}]  {position}\n{bar}")
    print(f"QUESTION: {task['question']}")
    print(f"KEYWORDS (all must appear): {task['answer_keywords']}")
    print(f"REFERENCE ANSWER: {task.get('reference_answer')}")
    if task["stale_keywords"]:
        print(f"STALE VALUE (outdated, from the internal note): {task['stale_keywords']}")
    if task["required_tools"]:
        print(f"REQUIRED TOOLS: {task['required_tools']}")
    if task["prompt_injection"]:
        print("(injection task: an injected passage is added in the injection condition)")

    evidence = ""
    for pid in task["supporting_passages"]:
        p = passages.get(pid)
        if p is None:
            print(f"\n!! supporting passage {pid} NOT FOUND")
            continue
        evidence += " " + p["text"]
        print(f"\n--- {pid}  {p['heading']}")
        print(textwrap.fill(p["text"][:PASSAGE_CHARS], 100))
        if len(p["text"]) > PASSAGE_CHARS:
            print("   [... passage continues]")
    for tid in task["ticket_ids"]:
        t = tickets.get(tid)
        evidence += " " + json.dumps(t or {})
        print(f"\n--- ticket {tid}: {t if t else 'NOT FOUND'}")

    if task["kind"] == "unanswerable":
        print("\nUNANSWERABLE: confirm the docs really do not answer this. Best BM25 matches:")
        for hit in index.search(task["question"], k=3):
            print(f"  {hit.passage.id}  {hit.passage.heading}: {hit.passage.text[:160]!r}")
        if not task["ticket_ids"]:
            print("  (no ticket id is listed for this task)")
    else:
        missing = [k for k in task["answer_keywords"] if not keyword_in(k, evidence)]
        if task["ticket_ids"] or task["kind"] != "multi_hop":
            status = "all keywords found in the evidence above" if not missing else f"MISSING: {missing}"
            print(f"\nAUTO-CHECK: {status}")
    print("\nChecklist: clear question? one right answer? evidence really says it? keywords not too loose?")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "heldout", "all"], default="heldout")
    ap.add_argument("--kind", default=None, help="only this kind, e.g. multi_hop")
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = ap.parse_args()

    data = args.data_dir
    tasks_path = data / "tasks.jsonl"
    tasks = load_jsonl(tasks_path)
    passages = {
        p["id"]: p for p in load_jsonl(data / "passages.jsonl") + load_jsonl(data / "internal_notes.jsonl")
    }
    tickets = {t["id"]: t for t in load_jsonl(data / "tickets.jsonl")}
    flags_path = data / "review_flags.jsonl"
    flagged = {f["task_id"] for f in load_jsonl(flags_path)} if flags_path.exists() else set()

    from taskbench.corpus import load_passages
    from taskbench.retrieval import BM25Index

    index = BM25Index(load_passages(data / "passages.jsonl") + load_passages(data / "internal_notes.jsonl"))

    def wanted(t: dict) -> bool:
        return (
            t["review_status"] == "draft"
            and t["id"] not in flagged
            and (args.split == "all" or t["split"] == args.split)
            and (args.kind is None or t["kind"] == args.kind)
        )

    todo = [t for t in tasks if wanted(t)]
    reviewed = sum(t["review_status"] == "reviewed" for t in tasks)
    print(f"{reviewed}/{len(tasks)} tasks reviewed so far; {len(todo)} to review now.")
    for n, task in enumerate(todo, 1):
        show(task, passages, tickets, index, f"({n} of {len(todo)})")
        while True:
            choice = input("\n[a]ccept  [f]lag  [s]kip  [q]uit > ").strip().lower()
            if choice in {"a", "f", "s", "q"}:
                break
        if choice == "q":
            break
        if choice == "a":
            mark_reviewed(tasks_path, task["id"])
            print(f"{task['id']} marked reviewed.")
        elif choice == "f":
            note = input("What is wrong? (one line) > ").strip()
            with flags_path.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"task_id": task["id"], "note": note}) + "\n")
            print(f"{task['id']} flagged (still a draft).")
    tasks = load_jsonl(tasks_path)
    print(f"\nDone for now: {sum(t['review_status'] == 'reviewed' for t in tasks)}/{len(tasks)} reviewed.")
    if flags_path.exists():
        print(f"Flagged tasks are listed in {flags_path}; tell Claude about them to fix.")


if __name__ == "__main__":
    main()
