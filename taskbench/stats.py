"""Aggregate result rows into the numbers the report shows.

Statistical choices (see docs/benchmark-methodology.md):

* Epochs are repeated measurements of the same task, not independent tasks.
  Confidence intervals therefore resample **tasks** (each task's epochs move
  together), never individual rows.
* Paired comparisons use only task IDs present in both configurations.
* Every rate is reported with its numerator and denominator.
* Metrics that do not apply are ``None`` and are excluded from denominators.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from taskbench.config import ModelPrice, token_cost
from taskbench.schema import ResultRow


def cost_per_success(total_cost_usd: float, successful_tasks: int) -> float | None:
    """Return cost per success; undefined (None) when there are no successes."""
    if not math.isfinite(total_cost_usd):
        raise ValueError("total_cost_usd must be a finite number")
    if successful_tasks < 0:
        raise ValueError("successful_tasks must be non-negative")
    if total_cost_usd < 0:
        raise ValueError("total_cost_usd must be non-negative")
    if successful_tasks == 0:
        return None
    return total_cost_usd / successful_tasks


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolated percentile (q in [0, 100]); None for no values."""
    if not values:
        return None
    if not 0 <= q <= 100:
        raise ValueError("q must be between 0 and 100")
    xs = sorted(values)
    pos = (len(xs) - 1) * q / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


@dataclass(frozen=True)
class Rate:
    """A proportion with its counts and an optional 95% interval."""

    numerator: int
    denominator: int
    ci_low: float | None = None
    ci_high: float | None = None

    @property
    def value(self) -> float | None:
        return None if self.denominator == 0 else self.numerator / self.denominator

    def fmt(self) -> str:
        if self.value is None:
            return "n/a (0 rows)"
        text = f"{self.value:.1%} ({self.numerator}/{self.denominator})"
        if self.ci_low is not None and self.ci_high is not None:
            text += f" [{self.ci_low:.1%}, {self.ci_high:.1%}]"
        return text


def _by_task(rows: Iterable[ResultRow], pred: Callable[[ResultRow], bool]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        groups[r.task_id].append(int(pred(r)))
    return groups


def cluster_bootstrap(
    groups: dict[str, list[int]], n_boot: int = 1000, seed: int = 0, alpha: float = 0.05
) -> tuple[float, float] | None:
    """Percentile bootstrap CI for a pooled rate, resampling whole task clusters."""
    keys = sorted(groups)
    if len(keys) < 2:
        return None
    rnd = random.Random(seed)
    stats: list[float] = []
    for _ in range(n_boot):
        num = den = 0
        for _ in keys:
            g = groups[keys[rnd.randrange(len(keys))]]
            num += sum(g)
            den += len(g)
        stats.append(num / den)
    lo = percentile(stats, 100 * alpha / 2)
    hi = percentile(stats, 100 * (1 - alpha / 2))
    assert lo is not None and hi is not None
    return lo, hi


def rate(
    rows: Sequence[ResultRow],
    pred: Callable[[ResultRow], bool],
    include: Callable[[ResultRow], bool] = lambda r: True,
    ci: bool = True,
    seed: int = 0,
) -> Rate:
    """Share of included rows satisfying ``pred``, with a task-clustered bootstrap CI."""
    kept = [r for r in rows if include(r)]
    num = sum(1 for r in kept if pred(r))
    interval = cluster_bootstrap(_by_task(kept, pred), seed=seed) if ci and kept else None
    return Rate(num, len(kept), *(interval or (None, None)))


def mean_of(values: Iterable[float | None]) -> tuple[float | None, int]:
    """Mean of non-None values and how many there were."""
    xs = [v for v in values if v is not None]
    return (sum(xs) / len(xs) if xs else None), len(xs)


@dataclass
class ConfigSummary:
    """All headline numbers for one (condition, config) group."""

    condition: str
    config: str
    rows: int
    tasks: int
    success: Rate
    by_kind: dict[str, Rate] = field(default_factory=dict)
    statuses: dict[str, int] = field(default_factory=dict)
    citation_precision: tuple[float | None, int] = (None, 0)
    no_citation_rows: int = 0
    retrieval_recall: tuple[float | None, int] = (None, 0)
    text_tool_call_rows: int = 0
    tool_calls: int = 0
    tool_validity: Rate | None = None
    required_tools: Rate | None = None
    recovery: Rate | None = None
    injection_resistance: Rate | None = None
    conflict_flagged: Rate | None = None
    latency_median_s: float | None = None
    latency_p95_s: float | None = None
    latency_p99_s: float | None = None
    mean_input_tokens: float | None = None
    mean_output_tokens: float | None = None
    total_cost_usd: float | None = None
    cost_per_success_usd: float | None = None
    reference_cost_per_success_usd: float | None = None


def summarize(
    rows: Sequence[ResultRow], reference_price: ModelPrice | None = None, seed: int = 0
) -> list[ConfigSummary]:
    """One summary per (condition, config), in a stable order."""
    groups: dict[tuple[str, str], list[ResultRow]] = defaultdict(list)
    for r in rows:
        groups[(r.condition, r.config)].append(r)
    order = {"baseline": 0, "rag": 1, "agent": 2, "agent_faults": 3}
    out: list[ConfigSummary] = []
    for (condition, config), g in sorted(groups.items(), key=lambda kv: (kv[0][0], order[kv[0][1]])):
        s = ConfigSummary(
            condition=condition,
            config=config,
            rows=len(g),
            tasks=len({r.task_id for r in g}),
            success=rate(g, lambda r: r.success, seed=seed),
        )
        for kind in sorted({r.kind for r in g}):
            s.by_kind[kind] = rate(g, lambda r: r.success, lambda r, k=kind: r.kind == k, ci=False)
        for r in g:
            s.statuses[r.status] = s.statuses.get(r.status, 0) + 1
        s.citation_precision = mean_of(r.citation_precision for r in g)
        s.no_citation_rows = sum(1 for r in g if r.cited_count == 0)
        s.retrieval_recall = mean_of(r.retrieval_recall for r in g)
        s.text_tool_call_rows = sum(1 for r in g if r.text_tool_call)
        s.tool_calls = sum(r.tool_calls for r in g)
        if s.tool_calls:
            invalid = sum(r.tool_calls_invalid for r in g)
            s.tool_validity = Rate(s.tool_calls - invalid, s.tool_calls)
        if any(r.required_tools_called is not None for r in g):
            s.required_tools = rate(
                g,
                lambda r: bool(r.required_tools_called),
                lambda r: r.required_tools_called is not None,
                ci=False,
            )
        if any(r.injected_faults for r in g):
            s.recovery = rate(g, lambda r: bool(r.recovered), lambda r: r.injected_faults > 0, seed=seed)
        if any(r.injection_exposed for r in g):
            s.injection_resistance = rate(
                g, lambda r: bool(r.injection_resisted), lambda r: r.injection_exposed, seed=seed
            )
        if any(r.conflict_flagged is not None for r in g):
            s.conflict_flagged = rate(
                g, lambda r: bool(r.conflict_flagged), lambda r: r.conflict_flagged is not None, ci=False
            )
        lat = [r.latency_s for r in g if r.latency_s is not None]
        s.latency_median_s = percentile(lat, 50)
        s.latency_p95_s = percentile(lat, 95)
        s.latency_p99_s = percentile(lat, 99) if len(lat) >= 200 else None
        s.mean_input_tokens = mean_of(r.input_tokens for r in g)[0]
        s.mean_output_tokens = mean_of(r.output_tokens for r in g)[0]
        costs = [r.estimated_cost_usd for r in g]
        if costs and all(c is not None for c in costs):
            s.total_cost_usd = sum(c for c in costs if c is not None)
            s.cost_per_success_usd = cost_per_success(s.total_cost_usd, s.success.numerator)
        if reference_price is not None:
            ref = [token_cost(reference_price, r.input_tokens, r.output_tokens) for r in g]
            if ref and all(c is not None for c in ref):
                total = sum(c for c in ref if c is not None)
                s.reference_cost_per_success_usd = cost_per_success(total, s.success.numerator)
        out.append(s)
    return out


@dataclass(frozen=True)
class PairedComparison:
    """Success-rate difference B - A on tasks both configurations attempted."""

    a: str
    b: str
    condition: str
    shared_tasks: int
    diff: float | None
    ci_low: float | None
    ci_high: float | None
    b_better: int
    a_better: int
    ties: int


def paired_comparison(
    rows: Sequence[ResultRow], a: str, b: str, condition: str = "main", n_boot: int = 1000, seed: int = 0
) -> PairedComparison:
    """Compare per-task mean success of ``b`` against ``a`` on shared task IDs."""

    def per_task(config: str) -> dict[str, float]:
        g: dict[str, list[int]] = defaultdict(list)
        for r in rows:
            if r.config == config and r.condition == condition:
                g[r.task_id].append(int(r.success))
        return {t: sum(v) / len(v) for t, v in g.items()}

    pa, pb = per_task(a), per_task(b)
    shared = sorted(set(pa) & set(pb))
    diffs = [pb[t] - pa[t] for t in shared]
    if not diffs:
        return PairedComparison(a, b, condition, 0, None, None, None, 0, 0, 0)
    rnd = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [diffs[rnd.randrange(len(diffs))] for _ in diffs]
        boots.append(sum(sample) / len(sample))
    return PairedComparison(
        a=a,
        b=b,
        condition=condition,
        shared_tasks=len(shared),
        diff=sum(diffs) / len(diffs),
        ci_low=percentile(boots, 2.5),
        ci_high=percentile(boots, 97.5),
        b_better=sum(1 for d in diffs if d > 0),
        a_better=sum(1 for d in diffs if d < 0),
        ties=sum(1 for d in diffs if d == 0),
    )


def _f(x: float | None, fmt: str = "{:.2f}") -> str:
    return "—" if x is None else fmt.format(x)


def summary_markdown(
    summaries: Sequence[ConfigSummary], comparisons: Sequence[PairedComparison], run_id: str
) -> str:
    """Render summaries as the Markdown table used in results/summary.md."""
    lines = [
        f"# Results summary: run `{run_id}`",
        "",
        "Generated by `taskbench stats`. Rates show numerator/denominator and a 95% "
        "bootstrap interval that resamples tasks. `—` means not applicable or not measured.",
        "",
        "| Condition | Config | Rows | Success | Citation precision (n) | Retrieval recall (n) | "
        "Tool validity | Recovery | Injection resisted | Median / p95 latency (s) | "
        "Mean in / out tokens | Cost per success (USD) | Ref. est. cost per success (USD) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        cp, cpn = s.citation_precision
        rr, rrn = s.retrieval_recall
        lines.append(
            f"| {s.condition} | {s.config} | {s.rows} | {s.success.fmt()} | "
            f"{_f(cp)} ({cpn}) | {_f(rr)} ({rrn}) | "
            f"{s.tool_validity.fmt() if s.tool_validity else '—'} | "
            f"{s.recovery.fmt() if s.recovery else '—'} | "
            f"{s.injection_resistance.fmt() if s.injection_resistance else '—'} | "
            f"{_f(s.latency_median_s)} / {_f(s.latency_p95_s)} | "
            f"{_f(s.mean_input_tokens, '{:.0f}')} / {_f(s.mean_output_tokens, '{:.0f}')} | "
            f"{_f(s.cost_per_success_usd, '{:.5f}')} | {_f(s.reference_cost_per_success_usd, '{:.5f}')} |"
        )
    lines += [
        "",
        "## Success by task kind",
        "",
        "| Condition | Config | " + " | ".join(sorted({k for s in summaries for k in s.by_kind})) + " |",
    ]
    kinds = sorted({k for s in summaries for k in s.by_kind})
    lines.append("|---|---|" + "---|" * len(kinds))
    for s in summaries:
        cells = [s.by_kind[k].fmt() if k in s.by_kind else "—" for k in kinds]
        lines.append(f"| {s.condition} | {s.config} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Execution status",
        "",
        "| Condition | Config | Statuses | No-citation rows | Tool call typed as text |",
        "|---|---|---|---|---|",
    ]
    for s in summaries:
        statuses = ", ".join(f"{k}: {v}" for k, v in sorted(s.statuses.items()))
        lines.append(
            f"| {s.condition} | {s.config} | {statuses} | {s.no_citation_rows} | {s.text_tool_call_rows} |"
        )
    if comparisons:
        lines += [
            "",
            "## Paired comparisons (B − A, per-task mean success)",
            "",
            "| A | B | Shared tasks | Difference [95% CI] | B better / A better / ties |",
            "|---|---|---|---|---|",
        ]
        for c in comparisons:
            diff = (
                "—"
                if c.diff is None
                else f"{c.diff:+.1%} [{_f(c.ci_low, '{:+.1%}')}, {_f(c.ci_high, '{:+.1%}')}]"
            )
            lines.append(
                f"| {c.a} | {c.b} | {c.shared_tasks} | {diff} | {c.b_better} / {c.a_better} / {c.ties} |"
            )
    return "\n".join(lines) + "\n"
