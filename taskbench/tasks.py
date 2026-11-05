"""Inspect task factory.

Run one configuration directly with Inspect:

    inspect eval taskbench/tasks.py@taskbench -T config=rag -T split=dev --model mockllm/model

or all of them through the project CLI (``taskbench run``), which also writes the
normalised results and the run manifest.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, get_args

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import GenerateConfig

from taskbench.config import BenchmarkConfig, load_config
from taskbench.dataset import extra_support, load_corpus, load_tasks, select_tasks
from taskbench.make_tickets import ensure_db
from taskbench.retrieval import BM25Index
from taskbench.schema import CONFIG_NAMES, BenchmarkTask, Condition, ConfigName, SplitName
from taskbench.scorers import judge_scorer, taskbench_scorer
from taskbench.solvers import PROMPT_VERSION, build_solver

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "configs" / "benchmark.yaml"


def to_sample(t: BenchmarkTask, extra_support: list[str] | None = None) -> Sample:
    """One Inspect sample per benchmark task; the full task travels in metadata.

    ``extra_support`` lists further passages that state the answer. They count as valid
    citations (never as retrieval targets); see ``passages_with_keywords``.
    """
    return Sample(
        id=t.id,
        input=t.question,
        target=t.reference_answer or " / ".join(t.answer_keywords),
        metadata={"task": t.model_dump(), "kind": t.kind, "extra_support": extra_support or []},
    )


def build_task(
    cfg: BenchmarkConfig,
    root: Path,
    config: ConfigName,
    split: SplitName,
    condition: Condition = "main",
    use_judge: bool = False,
) -> Task:
    """Build the Inspect Task for one configuration, split and condition."""
    if config not in CONFIG_NAMES:
        raise ValueError(f"unknown config {config!r}; expected one of {CONFIG_NAMES}")
    if condition == "injection" and config == "baseline":
        raise ValueError("the baseline sees no retrieved text, so it has no injection condition")
    ds = cfg.dataset
    tasks = select_tasks(load_tasks(root / ds.tasks_path), split, condition)
    if not tasks:
        raise ValueError(f"no tasks for split={split} condition={condition}")
    corpus = load_corpus(cfg, root, condition)
    index = BM25Index(corpus)
    extras = {t.id: extra_support(t, corpus) for t in tasks}
    db = ensure_db(root / ds.tickets_path, root / ds.tickets_db)
    scorers = [taskbench_scorer(config)]
    if use_judge:
        scorers.append(judge_scorer())
    return Task(
        name=f"taskbench_{config}_{condition}",
        dataset=MemoryDataset([to_sample(t, extras[t.id]) for t in tasks], name=f"{split}-{condition}"),
        solver=build_solver(
            config,
            index,
            db,
            k=cfg.retrieval.k,
            fault_probability=cfg.run.fault_probability,
            fault_seed=cfg.run.fault_seed,
        ),
        scorer=scorers,
        config=GenerateConfig(
            temperature=cfg.generation.temperature,
            max_tokens=cfg.generation.max_tokens,
            seed=cfg.generation.seed,
            max_connections=cfg.run.max_connections,
        ),
        message_limit=cfg.run.message_limit,
        time_limit=cfg.run.time_limit_s,
        fail_on_error=False,
        metadata={
            "config": config,
            "split": split,
            "condition": condition,
            "prompt_version": PROMPT_VERSION,
        },
    )


@task
def taskbench(
    config: str = "rag",
    split: str = "dev",
    condition: str = "main",
    config_path: str = str(DEFAULT_CONFIG),
) -> Task:
    """Entry point for ``inspect eval taskbench/tasks.py@taskbench -T config=...``."""
    path = Path(config_path).resolve()
    return build_task(
        load_config(path),
        path.parents[1],
        _choice(config, ConfigName),
        _choice(split, SplitName),
        _choice(condition, Condition),
    )


def _choice(value: str, literal: object) -> Any:
    """Validate a task argument against a Literal type (task args arrive as strings)."""
    allowed = get_args(literal)
    if value not in allowed:
        raise ValueError(f"{value!r} is not one of {allowed}")
    return value
