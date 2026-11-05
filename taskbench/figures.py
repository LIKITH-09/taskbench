"""Charts for the report. Matplotlib only, rendered off-screen."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from taskbench.stats import ConfigSummary

COLORS = {"baseline": "#8a8f98", "rag": "#3b6fd8", "agent": "#1f9d6b", "agent_faults": "#d9822b"}


def success_vs_tokens(summaries: Sequence[ConfigSummary], out: Path, condition: str = "main") -> Path | None:
    """Success rate (with 95% CI) against mean total tokens per attempt, one point per config.

    Tokens are always measured, so this chart works for local models where API
    cost is $0. Returns None when there is nothing to plot.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    points = [
        s
        for s in summaries
        if s.condition == condition
        and s.success.value is not None
        and s.mean_input_tokens is not None
        and s.mean_output_tokens is not None
    ]
    if not points:
        return None
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
    offsets = [(8, 6), (8, -14), (-8, 14), (-8, -20)]
    for i, s in enumerate(points):
        assert s.success.value is not None and s.mean_input_tokens is not None
        assert s.mean_output_tokens is not None
        x = s.mean_input_tokens + s.mean_output_tokens
        y = s.success.value
        lo = y - (s.success.ci_low if s.success.ci_low is not None else y)
        hi = (s.success.ci_high if s.success.ci_high is not None else y) - y
        ax.errorbar(x, y, yerr=[[lo], [hi]], fmt="o", capsize=4, color=COLORS.get(s.config, "black"))
        ax.annotate(
            s.config,
            (x, y),
            textcoords="offset points",
            xytext=offsets[i % len(offsets)],
            ha="left" if offsets[i % len(offsets)][0] > 0 else "right",
            fontsize=9,
        )
    ax.set_xlabel("Mean tokens per attempt (input + output)")
    ax.set_ylabel("Task success rate")
    ax.set_ylim(0, 1)
    ax.set_title(f"Success vs token use ({condition} condition, 95% task-bootstrap CI)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out
