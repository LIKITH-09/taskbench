"""Re-score unanswerable tasks with wider abstention phrasing (post-hoc, from stored answers).

    python scripts/sensitivity_abstention.py --run-id heldout-qwen25

Writes results/runs/<run-id>/sensitivity.md. The frozen scores in results.jsonl are not
changed; this is a labelled sensitivity analysis. No model is run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from taskbench.schema import ResultRow  # noqa: E402
from taskbench.sensitivity import rescore  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--results-dir", type=Path, default=ROOT / "results" / "runs")
    args = ap.parse_args()

    run = args.results_dir / args.run_id
    with (run / "results.jsonl").open(encoding="utf-8") as fh:
        rows = [ResultRow.model_validate(json.loads(line)) for line in fh if line.strip()]
    result = rescore(rows)

    lines = [
        f"# Abstention-phrasing sensitivity: run `{args.run_id}`",
        "",
        'Post-hoc analysis. The frozen scorer missed abstentions phrased as "not explicitly mentioned" '
        'or "no specific X mentioned" (found by blind human labelling). Only unanswerable rows change. '
        'Deflections such as "I can\'t check" are still not counted as abstentions.',
        "",
        "| Config | Unanswerable (frozen) | Unanswerable (wider) | Overall (frozen) | Overall (wider) |",
        "|---|---|---|---|---|",
    ]
    for s in result:
        lines.append(
            f"| {s.config} | {s.strict_success}/{s.unanswerable_rows} "
            f"({s.strict_success / max(s.unanswerable_rows, 1):.1%}) | "
            f"{s.wide_success}/{s.unanswerable_rows} "
            f"({s.wide_success / max(s.unanswerable_rows, 1):.1%}) | {s.total_strict}/{s.total_rows} "
            f"({s.total_strict / max(s.total_rows, 1):.1%}) | {s.total_wide}/{s.total_rows} "
            f"({s.total_wide / max(s.total_rows, 1):.1%}) |"
        )
    lines += ["", "## Rows that change to correct (check each by eye)", ""]
    for s in result:
        for r in s.changed:
            lines.append(f"- {s.config}/{r.task_id}/e{r.epoch}: {r.answer[:160].replace(chr(10), ' ')!r}")
    text = "\n".join(lines) + "\n"
    (run / "sensitivity.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {run / 'sensitivity.md'}")


if __name__ == "__main__":
    main()
