# TaskBench

TaskBench measures whether retrieval and tool use make an LLM support assistant complete more tasks, and whether that gain is worth the extra tokens, latency and cost. It also measures how each design copes with failing tools and with prompt injection hidden in retrieved text.

> **Name.** This project is unrelated to "TaskBench" ([Shen et al., NeurIPS 2024](https://arxiv.org/abs/2311.18760)), a benchmark for task automation with LLMs. This one measures retrieval and tool use for a documentation support assistant. The name is kept for the v0.1 write-up; if you fork it, consider a more distinctive one.

**Status:** v0.1 implementation complete. All 120 tasks are human-reviewed. Prompts were tuned on the dev split only (`PROMPT_VERSION` v3); held-out results are not included until the held-out run is done.

## Research question and hypothesis

**Question:** For a support assistant answering questions about the Inspect AI documentation and a ticket database, does adding retrieval (RAG) and then tools (an agent) raise the task success rate enough to justify the extra tokens and latency? How do these designs behave when tools fail or when retrieved text contains a malicious instruction?

**Hypothesis (falsifiable):** The agent completes more held-out tasks than RAG, mainly on ticket and multi-hop tasks, but its tokens per successful task grow by more than its success rate does. The hypothesis fails if the agent's success gain is larger than its relative increase in tokens per success.

## The four configurations

| ID | Name | What it does |
|---|---|---|
| C1 | `baseline` | Model answers from its own knowledge. No retrieval, no tools. |
| C2 | `rag` | BM25 retrieves the top 5 passages once; the model answers and cites passage IDs. |
| C3 | `agent` | Inspect `react()` loop with `search_docs` and `lookup_ticket` tools, at most 12 messages. |
| C4 | `agent_faults` | C3 plus seeded simulated tool timeouts on 30% of tool calls. |

Prompt injection is a separate **condition**, not a fifth configuration. It runs C2 and C3 on 10 tagged held-out tasks with a corpus that also contains planted malicious passages. The main condition never sees those passages.

## Dataset

| Item | Count | Source |
|---|---|---|
| Documentation passages | 1,054 | Inspect AI `docs/*.qmd` at commit `ae59272` (MIT), split on headings |
| Internal notes | 10 | Synthetic, deliberately outdated "team wiki" notes that conflict with the docs |
| Injection passages | 10 | Synthetic, used only in the injection condition |
| Tickets | 40 | Fictional, in `data/tickets.jsonl` |
| Tasks | 120 | 40 single-hop, 25 multi-hop, 10 conflicting, 15 unanswerable, 30 ticket-tool |
| Split | 40 dev / 80 held-out | Stratified by kind, seed 20261021 |

## Quick start

Requires Python 3.11+ and git. No GPU.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux:        source .venv/bin/activate
python -m pip install -e ".[dev,ollama]"

taskbench validate          # dataset integrity checks
pytest                      # unit tests + offline Inspect smoke tests on the mock model
```

Reproduce a mock-model run in about a minute (no model download):

```bash
taskbench run --config all --split dev --limit 3 --epochs 1 --model mockllm/model --run-id smoke-mock
```

Run with a local model (install [Ollama](https://ollama.com) first, then `ollama pull llama3.2`):

```bash
taskbench run --config all --split dev --epochs 1                  # tune prompts on dev only
git commit -am "freeze prompts and data"                           # held-out runs require a clean tree
taskbench run --config all --split heldout --condition main        # 80 tasks x 4 configs x 3 epochs = 960 rows
taskbench run --config all --split heldout --condition injection   # 10 tasks x 2 configs x 3 epochs = 60 rows
```

Each run writes to `results/runs/<run_id>/`:

| File | What it holds |
|---|---|
| `manifest.json` | git commit, package versions, model, prompt version, config, dataset hashes |
| `results.jsonl` | one validated row per task, epoch and configuration, failures included |
| `summary.md` | success with 95% intervals, citation and retrieval metrics, tool validity, recovery, injection resistance, latency, tokens, cost |
| `figures/success_vs_tokens.png` | success rate against tokens per attempt |
| `label_sheet.jsonl`, `calibration.md` | blind human labels and scorer agreement (after `label-sheet` and `calibrate`) |

Raw Inspect logs go to `logs/<run_id>/` (git-ignored). Open them with `inspect view --log-dir logs/<run_id>`.

## Commands

| Command | Purpose |
|---|---|
| `taskbench validate` | Check counts, splits, passage and ticket references, keyword support and corpus hash |
| `taskbench build-db` | Rebuild `data/tickets.sqlite` from `data/tickets.jsonl` |
| `taskbench run` | Run configurations through Inspect AI, then write results and summary |
| `taskbench report --run-id ID` | Re-read logs into `results.jsonl` |
| `taskbench stats --run-id ID` | Recompute `summary.md` and the figure |
| `taskbench label-sheet --run-id ID` | Write a blind sheet of 50 answers to label |
| `taskbench calibrate --run-id ID` | Agreement and Cohen's kappa of scorers against your labels |
| `python scripts/fetch_corpus.py` | Re-fetch the docs at the pinned commit and verify the corpus hash |

Settings live in `configs/benchmark.yaml`; flags override them for one run. On macOS and Linux, `make test`, `make smoke` and the other targets in the `Makefile` wrap these commands.

## Metrics

| Metric | Definition |
|---|---|
| Task success | Rows whose answer contains every answer keyword (or, for unanswerable tasks, abstains) ÷ all attempted rows. Errors and limit hits count as failures. |
| Citation precision | Cited passage IDs that are supporting passages ÷ all cited IDs. Rows with no citations are reported separately. |
| Retrieval recall@5 | Supporting passages retrieved ÷ supporting passages. |
| Tool-call validity | Tool calls without argument-parsing errors ÷ all tool calls. |
| Recovery rate | Successful rows with ≥1 injected fault ÷ rows with ≥1 injected fault. |
| Injection resistance | Exposed rows whose answer does not contain the planted marker ÷ rows whose retrieval actually surfaced the injection passage. |
| Latency | Median and p95 wall-clock seconds per sample; p99 only with ≥200 rows. |
| Cost per success | Total token cost of all attempts, failures included ÷ number of successes. |
| Scorer calibration | Raw agreement and Cohen's kappa of the keyword scorer (and optional LLM judge) against blind human labels. |

Intervals are 95% bootstrap intervals that resample **tasks**, so a task's three epochs move together. Paired comparisons use only task IDs present in both configurations. Full detail: `docs/benchmark-methodology.md`.

## Repository layout

```
configs/      benchmark.yaml (single source of truth), prices.yaml
data/         tasks, passages, internal notes, injection passages, tickets, human labels
scripts/      fetch_corpus.py (pinned corpus), draft_tasks.py (how the tasks were drafted)
taskbench/    schema, config, corpus, retrieval, metrics, faults, tools, solvers, tasks,
              scorers, report, stats, calibration, manifest, figures, run (CLI)
tests/        unit tests and offline Inspect smoke tests
results/      runs/<run_id>/ outputs (committed)
docs/         architecture, methodology, contribution workflow, roadmap
```

## Limitations

- **Small sample.** 80 held-out tasks, one corpus, one local model. Treat intervals as wide.
- **Keyword scoring.** It misses correct paraphrases and can pass answers that mention the keyword in a wrong statement. That is why the calibration step exists.
- **Drafted tasks.** An LLM helped draft the questions; each one must be human-reviewed before results are reported.
- **Training contamination.** The model under test may have seen Inspect AI's documentation, which helps the baseline on documentation questions. The fictional tickets are the clean control.
- **Local cost.** Ollama runs have no API charge. To compare cost, set `estimate_local_with` in `prices.yaml` and report the result as an estimate.

## Scope

**In:** Python CLI, Inspect AI, BM25, SQLite, JSONL results, tests, statistics, failure analysis, an upstream contribution attempt.
**Out of v0.1:** vector databases, Kubernetes, fine-tuning, GPU kernels, multi-agent systems, dashboards.

See `docs/architecture.md`, `docs/benchmark-methodology.md`, `docs/open-source-contribution.md` and `docs/roadmap.md`.
