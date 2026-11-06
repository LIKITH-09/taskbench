"""Blind human labelling of model answers (see "Human labels" in data/README.md).

Steps:

    taskbench label-sheet --run-id heldout-qwen25
    python scripts/label_answers.py --run-id heldout-qwen25 --labeler YOUR-NAME

Do this BEFORE you read summary.md, so the automatic scores cannot influence you. The
sheet shows only the question, the reference answer and the model's answer.

For each answer decide whether it is correct *by meaning*, not by matching words:

    c   correct: it gives the right answer to the question
    i   incorrect: wrong, missing, vague, or not an answer
    s   skip for now
    q   quit (progress is saved after every answer)

Rules of thumb:
  * Unanswerable questions (reference answer "I don't know"): correct only if the
    answer says it does not know / cannot find it. A confident made-up answer is incorrect.
  * Conflicting questions: correct only if it gives the official documentation's value
    (see the reference answer). Mentioning the outdated value as outdated is fine.
  * Ticket questions: correct only if the ticket facts match the reference record.
  * An answer that contains the right words but contradicts itself is incorrect.

Labelled rows are saved to data/human_labels.jsonl after every answer.
"""

from __future__ import annotations

import argparse
import json
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL_FIELDS = ("run_id", "config", "task_id", "epoch", "label", "labeler", "notes")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """Write rows as JSON lines, tolerating Windows file locks (retry, then write directly)."""
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    for _ in range(6):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            time.sleep(0.5)
    path.write_text(text, encoding="utf-8", newline="\n")
    try:
        tmp.unlink()
    except OSError:
        pass


def save_all(sheet_path: Path, sheet: list[dict], labels_path: Path) -> None:
    write_jsonl(sheet_path, sheet)
    done = [{k: r[k] for k in LABEL_FIELDS} for r in sheet if r.get("label")]
    write_jsonl(labels_path, done)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--labeler", required=True, help="your name or handle, stored with each label")
    ap.add_argument("--results-dir", type=Path, default=ROOT / "results" / "runs")
    ap.add_argument("--labels-path", type=Path, default=ROOT / "data" / "human_labels.jsonl")
    args = ap.parse_args()

    sheet_path = args.results_dir / args.run_id / "label_sheet.jsonl"
    if not sheet_path.exists():
        raise SystemExit(f"{sheet_path} not found. Run: taskbench label-sheet --run-id {args.run_id}")
    sheet = read_jsonl(sheet_path)
    todo = [r for r in sheet if not r.get("label")]
    print(f"{len(sheet) - len(todo)}/{len(sheet)} answers labelled so far; {len(todo)} to go.")
    print("Do not open summary.md until you have finished labelling.")

    for n, row in enumerate(todo, 1):
        bar = "=" * 78
        print(f"\n{bar}\nAnswer {len(sheet) - len(todo) + n} of {len(sheet)}\n{bar}")
        print(f"QUESTION: {row['question']}")
        print(f"REFERENCE ANSWER: {row['reference_answer']}")
        print("\nMODEL ANSWER:")
        print(textwrap.fill(row["answer"] or "(empty)", 100))
        while True:
            choice = input("\n[c]orrect  [i]ncorrect  [s]kip  [q]uit > ").strip().lower()
            if choice in {"c", "i", "s", "q"}:
                break
        if choice == "q":
            break
        if choice == "s":
            continue
        row["label"] = "correct" if choice == "c" else "incorrect"
        row["labeler"] = args.labeler
        save_all(sheet_path, sheet, args.labels_path)

    save_all(sheet_path, sheet, args.labels_path)
    done = sum(1 for r in sheet if r.get("label"))
    print(f"\nLabelled {done}/{len(sheet)}. Saved to {args.labels_path}.")
    if done == len(sheet):
        print(f"All done. Now run: taskbench calibrate --run-id {args.run_id}")


if __name__ == "__main__":
    main()
