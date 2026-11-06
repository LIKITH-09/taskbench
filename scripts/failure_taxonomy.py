"""Count and sample failure categories for one epoch of a run (first pass, automatic).

    python scripts/failure_taxonomy.py --run-id heldout-qwen25

Writes results/runs/<run-id>/failure_taxonomy.md with counts per configuration and a few
example answers per category. Read the examples before quoting any category in the report.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from taskbench.dataset import load_tasks  # noqa: E402
from taskbench.schema import ResultRow  # noqa: E402
from taskbench.taxonomy import ORDER, categorise, counts  # noqa: E402

EXAMPLES = 3


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--epoch", type=int, default=1)
    ap.add_argument("--results-dir", type=Path, default=ROOT / "results" / "runs")
    ap.add_argument("--tasks-path", type=Path, default=ROOT / "data" / "tasks.jsonl")
    args = ap.parse_args()

    run = args.results_dir / args.run_id
    with (run / "results.jsonl").open(encoding="utf-8") as fh:
        rows = [ResultRow.model_validate(json.loads(line)) for line in fh if line.strip()]
    tasks = {t.id: t for t in load_tasks(args.tasks_path)}
    grouped = categorise(rows, tasks, args.epoch)

    lines = [
        f"# Failure categories: run `{args.run_id}`, epoch {args.epoch}",
        "",
        "Automatic first pass: each failed main-condition row gets the first category that fits. "
        "Verify the examples by eye before quoting them.",
        "",
    ]
    configs = [c for c in ("baseline", "rag", "agent", "agent_faults") if c in grouped]
    lines += ["| Category | " + " | ".join(configs) + " |", "|---|" + "---|" * len(configs)]
    per = {c: counts(grouped[c]) for c in configs}
    for cat in ORDER:
        if any(per[c][cat] for c in configs):
            lines.append(f"| {cat} | " + " | ".join(str(per[c][cat]) for c in configs) + " |")
    lines.append("| **Total failed rows** | " + " | ".join(f"**{len(grouped[c])}**" for c in configs) + " |")

    lines += ["", "## Examples", ""]
    for config in configs:
        for cat in ORDER:
            picks = [r for c, r in grouped[config] if c == cat][:EXAMPLES]
            if not picks:
                continue
            lines.append(f"### {config}: {cat}")
            for r in picks:
                answer = r.answer[:200].replace(chr(10), " ")
                lines.append(f"- {r.task_id} ({r.kind}): {answer!r}")
            lines.append("")
    text = "\n".join(lines) + "\n"
    (run / "failure_taxonomy.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {run / 'failure_taxonomy.md'}")


if __name__ == "__main__":
    main()
