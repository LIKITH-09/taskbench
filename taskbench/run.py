"""TaskBench command-line interface.

    taskbench validate                          check dataset integrity
    taskbench build-db                          build data/tickets.sqlite
    taskbench run --config all --split dev      run configurations with Inspect AI
    taskbench report --run-id ID                logs -> results.jsonl
    taskbench stats --run-id ID                 results.jsonl -> summary.md + figure
    taskbench label-sheet --run-id ID           blind sheet for human labelling
    taskbench calibrate --run-id ID             agreement of scorers with human labels

Defaults come from configs/benchmark.yaml; flags override them for one run.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from taskbench.config import BenchmarkConfig, load_config, load_prices
from taskbench.dataset import load_tasks, validate_dataset, write_jsonl
from taskbench.schema import CONFIG_NAMES, HumanLabel, ResultRow

DEFAULT_CONFIG = Path("configs") / "benchmark.yaml"
# Project root: the directory that holds configs/. Set from --config-file in main().
ROOT = Path.cwd()


def run_dir(run_id: str) -> Path:
    return ROOT / "results" / "runs" / run_id


def load_rows(run_id: str) -> list[ResultRow]:
    path = run_dir(run_id) / "results.jsonl"
    if not path.exists():
        raise SystemExit(f"{path} not found; run `taskbench report --run-id {run_id}` first")
    with path.open(encoding="utf-8") as f:
        return [ResultRow.model_validate_json(line) for line in f if line.strip()]


def cmd_validate(cfg: BenchmarkConfig, args: argparse.Namespace) -> int:
    problems = validate_dataset(cfg, ROOT)
    for p in problems:
        print(f"problem: {p}")
    tasks = load_tasks(ROOT / cfg.dataset.tasks_path)
    drafts = sum(t.review_status == "draft" for t in tasks)
    print(f"{len(tasks)} tasks, {len(problems)} problems, {drafts} still marked draft")
    if drafts:
        print("note: review draft tasks and set review_status to 'reviewed' before held-out runs")
    return 1 if problems else 0


def cmd_build_db(cfg: BenchmarkConfig, args: argparse.Namespace) -> int:
    from taskbench.make_tickets import build_db, load_tickets

    tickets = load_tickets(ROOT / cfg.dataset.tickets_path)
    build_db(tickets, ROOT / cfg.dataset.tickets_db)
    print(f"built {cfg.dataset.tickets_db} with {len(tickets)} tickets")
    return 0


def cmd_run(cfg: BenchmarkConfig, args: argparse.Namespace) -> int:
    from inspect_ai import eval as inspect_eval

    from taskbench.manifest import build_manifest, git_state
    from taskbench.tasks import build_task

    problems = validate_dataset(cfg, ROOT)
    if problems:
        print("dataset problems; fix them before running:\n  " + "\n  ".join(problems))
        return 1
    if args.split == "heldout" and not args.allow_dirty:
        state = git_state(ROOT)
        if state["dirty"] is not False:
            print(
                "held-out runs require a clean, committed git tree so the run is reproducible.\n"
                "Commit your changes (or pass --allow-dirty for a throwaway run)."
            )
            return 1

    model = args.model or cfg.run.model
    judge = args.judge_model or cfg.judge.model
    if judge and judge == model:
        print("the judge model must differ from the model under test")
        return 1
    configs = list(CONFIG_NAMES) if args.config == "all" else [args.config]
    conditions = ["main", "injection"] if args.condition == "all" else [args.condition]
    epochs = args.epochs or cfg.run.epochs
    run_id = args.run_id or f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}_{args.split}"
    out = run_dir(run_id)
    if out.exists() and any(out.iterdir()):
        print(f"{out} already exists; choose another --run-id")
        return 1

    tasks = []
    for condition in conditions:
        for config in configs:
            if condition == "injection" and config not in ("rag", "agent"):
                continue  # baseline sees no passages; agent_faults would mix two effects
            tasks.append(build_task(cfg, ROOT, config, args.split, condition, use_judge=bool(judge)))

    out.mkdir(parents=True, exist_ok=True)
    prices = load_prices(ROOT / cfg.prices_path)
    manifest = build_manifest(
        run_id=run_id,
        root=ROOT,
        cfg=cfg,
        prices=prices,
        model=model,
        judge_model=judge,
        configs=configs,
        conditions=conditions,
        split=args.split,
        epochs=epochs,
        limit=args.limit,
        argv=sys.argv,
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    log_dir = ROOT / cfg.run.log_dir / run_id
    inspect_eval(
        tasks,
        model=model,
        model_roles={"grader": judge} if judge else None,
        log_dir=str(log_dir),
        epochs=epochs,
        limit=args.limit,
        fail_on_error=False,
        tags=[run_id, args.split],
    )
    args.run_id = run_id
    cmd_report(cfg, args)
    return cmd_stats(cfg, args)


def cmd_report(cfg: BenchmarkConfig, args: argparse.Namespace) -> int:
    from taskbench.report import rows_from_log_dir

    prices = load_prices(ROOT / cfg.prices_path)
    rows = rows_from_log_dir(ROOT / cfg.run.log_dir / args.run_id, args.run_id, prices)
    path = run_dir(args.run_id) / "results.jsonl"
    write_jsonl([r.model_dump() for r in rows], path)
    print(f"wrote {len(rows)} rows to {path.relative_to(ROOT)}")
    return 0


def cmd_stats(cfg: BenchmarkConfig, args: argparse.Namespace) -> int:
    from taskbench.figures import success_vs_tokens
    from taskbench.stats import paired_comparison, summarize, summary_markdown

    rows = load_rows(args.run_id)
    prices = load_prices(ROOT / cfg.prices_path)
    summaries = summarize(rows, reference_price=prices.reference_price(), seed=cfg.generation.seed)
    present = {r.config for r in rows if r.condition == "main"}
    pairs = [("baseline", "rag"), ("rag", "agent"), ("agent", "agent_faults")]
    comparisons = [
        paired_comparison(rows, a, b, seed=cfg.generation.seed)
        for a, b in pairs
        if a in present and b in present
    ]
    out = run_dir(args.run_id)
    (out / "summary.md").write_text(summary_markdown(summaries, comparisons, args.run_id), encoding="utf-8")
    fig = success_vs_tokens(summaries, out / "figures" / "success_vs_tokens.png")
    print(
        f"wrote {(out / 'summary.md').relative_to(ROOT)}" + (f" and {fig.relative_to(ROOT)}" if fig else "")
    )
    return 0


def cmd_label_sheet(cfg: BenchmarkConfig, args: argparse.Namespace) -> int:
    from taskbench.calibration import label_sheet

    rows = load_rows(args.run_id)
    tasks = {t.id: t for t in load_tasks(ROOT / cfg.dataset.tasks_path)}
    sheet = label_sheet(rows, tasks, n=args.n, seed=cfg.generation.seed)
    path = run_dir(args.run_id) / "label_sheet.jsonl"
    write_jsonl(sheet, path)
    print(
        f"wrote {len(sheet)} rows to {path.relative_to(ROOT)}; fill in 'label' and 'labeler', "
        f"then save the labelled rows to {cfg.dataset.human_labels_path}"
    )
    return 0


def cmd_calibrate(cfg: BenchmarkConfig, args: argparse.Namespace) -> int:
    from taskbench.calibration import calibrate

    rows = load_rows(args.run_id)
    path = ROOT / cfg.dataset.human_labels_path
    with path.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    unlabelled = sum(1 for r in records if not r.get("label"))
    labels = [
        HumanLabel.model_validate({k: v for k, v in r.items() if k in HumanLabel.model_fields})
        for r in records
        if r.get("label")
    ]
    if unlabelled:
        print(f"skipping {unlabelled} rows with no label")
    result = calibrate(labels, rows)

    def fmt(x: float | None) -> str:
        return "—" if x is None else f"{x:.3f}"

    lines = [
        f"# Scorer calibration: run `{args.run_id}`",
        "",
        f"Human labels: {result.n_labels} ({result.n_matched} matched to result rows).",
        "",
        "| Scorer | n | Agreement | Cohen's kappa |",
        "|---|---|---|---|",
        f"| Deterministic keyword scorer | {result.n_matched} | {fmt(result.deterministic_agreement)} "
        f"| {fmt(result.deterministic_kappa)} |",
        f"| LLM judge | {result.judge_n} | {fmt(result.judge_agreement)} | {fmt(result.judge_kappa)} |",
        "",
        "## Disagreements with the deterministic scorer",
        "",
        *(f"- {d}" for d in result.disagreements or ["none"]),
    ]
    out = run_dir(args.run_id) / "calibration.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="taskbench", description=__doc__.splitlines()[0])
    parser.add_argument("--config-file", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="check dataset integrity")
    sub.add_parser("build-db", help="build the ticket database")

    run = sub.add_parser("run", help="run configurations with Inspect AI")
    run.add_argument("--config", choices=[*CONFIG_NAMES, "all"], default="all")
    run.add_argument("--split", choices=["dev", "heldout"], default="dev")
    run.add_argument("--condition", choices=["main", "injection", "all"], default="main")
    run.add_argument("--epochs", type=int, default=None, help="default: run.epochs in the config")
    run.add_argument("--limit", type=int, default=None, help="only the first N tasks (smoke tests)")
    run.add_argument("--model", default=None, help="default: run.model in the config")
    run.add_argument("--judge-model", default=None, help="default: judge.model in the config")
    run.add_argument("--run-id", default=None)
    run.add_argument(
        "--allow-dirty", action="store_true", help="allow held-out runs with uncommitted changes"
    )

    for name in ("report", "stats"):
        p = sub.add_parser(name)
        p.add_argument("--run-id", required=True)
    sheet = sub.add_parser("label-sheet", help="write a blind sheet for human labelling")
    sheet.add_argument("--run-id", required=True)
    sheet.add_argument("--n", type=int, default=50)
    cal = sub.add_parser("calibrate", help="compare scorers with human labels")
    cal.add_argument("--run-id", required=True)
    return parser


COMMANDS = {
    "validate": cmd_validate,
    "build-db": cmd_build_db,
    "run": cmd_run,
    "report": cmd_report,
    "stats": cmd_stats,
    "label-sheet": cmd_label_sheet,
    "calibrate": cmd_calibrate,
}


def main(argv: list[str] | None = None) -> None:
    global ROOT
    args = build_parser().parse_args(argv)
    if getattr(args, "epochs", None) is not None and args.epochs < 1:
        raise SystemExit("--epochs must be >= 1")
    if getattr(args, "limit", None) is not None and args.limit < 1:
        raise SystemExit("--limit must be >= 1")
    config_file = args.config_file.resolve()
    if not config_file.exists():
        raise SystemExit(f"{config_file} not found; run from the project root or pass --config-file")
    ROOT = config_file.parents[1]
    cfg = load_config(config_file)
    raise SystemExit(COMMANDS[args.command](cfg, args))


if __name__ == "__main__":
    main()
