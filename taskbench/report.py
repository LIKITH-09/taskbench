"""Normalise raw Inspect logs into one validated ResultRow per sample and epoch.

Failed samples are kept: an errored sample becomes a row with status "error"
and success False, and a sample that hit a limit becomes status
"limit_reached". Nothing is dropped silently; ``rows_from_samples`` raises if a
sample cannot be turned into a valid row.

``row_from_sample`` works on the plain-dict form of an Inspect ``EvalSample`` so
it can be unit tested without running a model.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast

from taskbench.config import ModelPrice, token_cost
from taskbench.schema import CONFIG_NAMES, BenchmarkTask, Condition, ConfigName, ResultRow, RunStatus

SCORER = "taskbench_scorer"
JUDGE = "model_graded_qa"
ANSWER_CHARS = 2000


def parse_task_name(name: str) -> tuple[ConfigName, Condition]:
    """Recover (config, condition) from a task name such as ``taskbench_agent_faults_main``."""
    prefix = "taskbench_"
    if not name.startswith(prefix):
        raise ValueError(f"not a TaskBench task: {name!r}")
    body = name[len(prefix) :]
    for condition in ("main", "injection"):
        suffix = f"_{condition}"
        if body.endswith(suffix):
            config = body[: -len(suffix)]
            if config in CONFIG_NAMES:
                return cast(ConfigName, config), cast(Condition, condition)
    raise ValueError(f"cannot parse config/condition from {name!r}")


def _score(scores: Mapping[str, Any], name: str) -> Mapping[str, Any] | None:
    """A score by scorer name, tolerating a registry prefix such as ``pkg/name``."""
    for key, value in scores.items():
        if key == name or key.split("/")[-1] == name:
            return value
    return None


def _usage(sample: Mapping[str, Any], model: str) -> tuple[int | None, int | None]:
    usage = (sample.get("model_usage") or {}).get(model)
    if not usage:
        return None, None
    # Inspect's ``input_tokens`` excludes tokens served from or written to the provider's
    # prompt cache (Ollama and OpenAI-compatible servers report cached prompt tokens
    # separately). The true prompt size is the sum, so count all three.
    prompt = (
        int(usage.get("input_tokens", 0))
        + int(usage.get("input_tokens_cache_read") or 0)
        + int(usage.get("input_tokens_cache_write") or 0)
    )
    return prompt, int(usage.get("output_tokens", 0))


def row_from_sample(
    sample: Mapping[str, Any],
    *,
    run_id: str,
    config: ConfigName,
    condition: Condition,
    model: str,
    price: ModelPrice | None,
) -> ResultRow:
    """Build one ResultRow from the dict form of an EvalSample."""
    task = BenchmarkTask.model_validate(sample["metadata"]["task"])
    error = sample.get("error")
    limit = sample.get("limit")
    scores = sample.get("scores") or {}
    main = _score(scores, SCORER)
    meta: dict[str, Any] = dict((main or {}).get("metadata") or {})
    answer = str((main or {}).get("answer") or (sample.get("output") or {}).get("completion") or "")

    status: RunStatus
    error_type: str | None
    if error:
        status, error_type = "error", str(error.get("message", "error"))[:200]
    elif limit:
        status, error_type = "limit_reached", f"limit:{limit.get('type', 'unknown')}"
    elif main is None:
        status, error_type = "error", "not_scored"
    else:
        status, error_type = "success", None

    success = status == "success" and main is not None and main.get("value") == "C"
    judge = _score(scores, JUDGE)
    in_tok, out_tok = _usage(sample, model)
    faults = int(meta.get("injected_faults", 0) or 0)
    exposed = bool(meta.get("injection_exposed", False))
    tool_calls = int(meta.get("tool_calls", 0) or 0)

    return ResultRow(
        run_id=run_id,
        config=config,
        condition=condition,
        model=model,
        task_id=task.id,
        split=task.split,
        kind=task.kind,
        epoch=int(sample["epoch"]),
        status=status,
        error_type=error_type,
        success=success,
        abstained=bool(meta.get("abstained", False)),
        conflict_flagged=meta.get("conflict_flagged"),
        judged_success=None if judge is None else judge.get("value") == "C",
        cited_count=meta.get("cited_count"),
        citation_precision=meta.get("citation_precision"),
        retrieval_recall=meta.get("retrieval_recall"),
        text_tool_call=meta.get("text_tool_call"),
        tool_calls=tool_calls,
        tool_calls_invalid=min(int(meta.get("tool_calls_invalid", 0) or 0), tool_calls),
        tool_errors=min(int(meta.get("tool_errors", 0) or 0), tool_calls),
        required_tools_called=meta.get("required_tools_called"),
        injected_faults=faults,
        recovered=(success if faults > 0 else None),
        injection_exposed=exposed,
        injection_resisted=meta.get("injection_resisted") if exposed else None,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_s=sample.get("total_time"),
        estimated_cost_usd=token_cost(price, in_tok, out_tok),
        answer=answer[:ANSWER_CHARS],
    )


def rows_from_samples(
    samples: Iterable[Mapping[str, Any]],
    *,
    run_id: str,
    task_name: str,
    model: str,
    price: ModelPrice | None,
) -> list[ResultRow]:
    """Rows for every sample of one log."""
    config, condition = parse_task_name(task_name)
    return [
        row_from_sample(s, run_id=run_id, config=config, condition=condition, model=model, price=price)
        for s in samples
    ]


def rows_from_log_dir(log_dir: Path, run_id: str, prices: Any) -> list[ResultRow]:
    """Read every Inspect log in ``log_dir`` and return all result rows.

    Imports Inspect lazily so the pure functions above stay importable without it.
    """
    from inspect_ai.log import list_eval_logs, read_eval_log

    rows: list[ResultRow] = []
    infos = list_eval_logs(str(log_dir), recursive=True, descending=False)
    if not infos:
        raise FileNotFoundError(f"no Inspect logs found in {log_dir}")
    for info in infos:
        log = read_eval_log(info)
        if log.status != "success":
            # A whole-task failure still has per-sample records worth keeping.
            print(f"warning: log {info.name} has status {log.status}")
        samples = [
            s.model_dump(
                mode="json",
                include={
                    "id",
                    "epoch",
                    "metadata",
                    "scores",
                    "error",
                    "limit",
                    "model_usage",
                    "total_time",
                    "output",
                },
            )
            for s in (log.samples or [])
        ]
        rows += rows_from_samples(
            samples,
            run_id=run_id,
            task_name=log.eval.task.split("/")[-1],
            model=log.eval.model,
            price=prices.price_for(log.eval.model),
        )
    return rows
