"""End-to-end runs through Inspect AI on its offline mock model.

These need inspect-ai installed but no network and no GPU. They exercise the real
solvers, tools, scorer, log files and report together:

* every configuration runs and yields one valid row per sample
* the agent really calls lookup_ticket and is scored correct
* fault injection is recorded and counted as a failed recovery
* injection exposure and the followed instruction are detected

The live-model test at the bottom runs only when TASKBENCH_OLLAMA=1.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("inspect_ai")

from inspect_ai import eval as inspect_eval  # noqa: E402
from inspect_ai.model import ModelOutput, get_model  # noqa: E402

from taskbench.config import BenchmarkConfig, load_prices  # noqa: E402
from taskbench.report import rows_from_log_dir  # noqa: E402
from taskbench.schema import ResultRow  # noqa: E402
from taskbench.tasks import build_task  # noqa: E402

pytestmark = pytest.mark.inspect
MOCK = "mockllm/model"


def run(
    root: Path,
    cfg: BenchmarkConfig,
    config: str,
    *,
    condition: str = "main",
    sample_id: str | None = None,
    outputs: list[ModelOutput] | None = None,
) -> list[ResultRow]:
    log_dir = root / "logs" / f"{config}-{condition}-{sample_id}"
    model = get_model(MOCK, custom_outputs=outputs, memoize=False) if outputs else MOCK
    inspect_eval(
        build_task(cfg, root, config, "heldout", condition),
        model=model,
        log_dir=str(log_dir),
        sample_id=sample_id,
        display="none",
    )
    return rows_from_log_dir(log_dir, "smoke", load_prices(root / "configs" / "prices.yaml"))


@pytest.mark.parametrize("config", ["baseline", "rag", "agent", "agent_faults"])
def test_every_config_yields_one_row_per_sample(mini_root: Path, mini_cfg: BenchmarkConfig, config: str):
    rows = run(mini_root, mini_cfg, config)
    heldout = 5
    assert len(rows) == heldout
    assert all(r.config == config and r.condition == "main" for r in rows)
    # The mock's default text contains no answer keywords and does not abstain.
    assert not any(r.success for r in rows)
    if config == "baseline":
        assert all(r.citation_precision is None and r.retrieval_recall is None for r in rows)
    if config == "rag":
        assert any(r.retrieval_recall is not None for r in rows)


def test_agent_calls_ticket_tool_and_succeeds(mini_root: Path, mini_cfg: BenchmarkConfig):
    outputs = [
        ModelOutput.for_tool_call(MOCK, "lookup_ticket", {"ticket_id": "TCK-1001"}),
        ModelOutput.from_content(MOCK, "Ticket TCK-1001 is owned by Priya."),
    ]
    (row,) = run(mini_root, mini_cfg, "agent", sample_id="Q0006", outputs=outputs)
    assert row.status == "success" and row.success
    assert row.tool_calls == 1 and row.tool_errors == 0
    assert row.required_tools_called is True
    assert row.injected_faults == 0 and row.recovered is None


def test_missing_ticket_is_a_tool_error_not_a_crash(mini_root: Path, mini_cfg: BenchmarkConfig):
    outputs = [
        ModelOutput.for_tool_call(MOCK, "lookup_ticket", {"ticket_id": "TCK-4040"}),
        ModelOutput.from_content(MOCK, "I don't know."),
    ]
    (row,) = run(mini_root, mini_cfg, "agent", sample_id="Q0006", outputs=outputs)
    assert row.status == "success" and not row.success
    assert row.tool_errors == 1


def test_injected_fault_is_recorded(mini_root: Path, mini_cfg: BenchmarkConfig):
    always = mini_cfg.model_copy(update={"run": mini_cfg.run.model_copy(update={"fault_probability": 1.0})})
    outputs = [
        ModelOutput.for_tool_call(MOCK, "lookup_ticket", {"ticket_id": "TCK-1001"}),
        ModelOutput.from_content(MOCK, "I don't know."),
    ]
    (row,) = run(mini_root, always, "agent_faults", sample_id="Q0006", outputs=outputs)
    assert row.injected_faults == 1
    assert row.recovered is False
    assert row.tool_errors == 0  # the injected timeout is not counted as a real tool error


def test_injection_exposure_and_following_detected(mini_root: Path, mini_cfg: BenchmarkConfig):
    outputs = [ModelOutput.from_content(MOCK, "ZEBRA-1111")]
    (row,) = run(mini_root, mini_cfg, "rag", condition="injection", sample_id="Q0002", outputs=outputs)
    assert row.condition == "injection"
    assert row.injection_exposed is True
    assert row.injection_resisted is False


def test_baseline_has_no_injection_condition(mini_root: Path, mini_cfg: BenchmarkConfig):
    with pytest.raises(ValueError, match="baseline"):
        build_task(mini_cfg, mini_root, "baseline", "heldout", "injection")


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("TASKBENCH_OLLAMA") != "1", reason="set TASKBENCH_OLLAMA=1 to run")
def test_live_ollama_rag_dev(mini_root: Path, mini_cfg: BenchmarkConfig):
    log_dir = mini_root / "logs" / "live"
    inspect_eval(
        build_task(mini_cfg, mini_root, "rag", "dev"),
        model="ollama/llama3.2",
        log_dir=str(log_dir),
        display="none",
    )
    rows = rows_from_log_dir(log_dir, "live", load_prices(mini_root / "configs" / "prices.yaml"))
    assert len(rows) == 1 and rows[0].input_tokens
