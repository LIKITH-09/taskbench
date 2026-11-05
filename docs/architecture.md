# Architecture

TaskBench is a thin layer over Inspect AI. Inspect runs models, tools and logging; TaskBench supplies the dataset, the four solver chains, one scorer, and the code that turns logs into statistics.

```text
configs/benchmark.yaml ──► config.py (validated settings)
                                │
data/*.jsonl ──► dataset.py ──► validate_dataset()  ◄── taskbench validate, CI
                     │
                     ▼
          tasks.py build_task(config, split, condition)
            ├─ retrieval.py  BM25 index over docs + notes (+ injection passages)
            ├─ make_tickets.py  SQLite built from tickets.jsonl
            ├─ solvers.py   C1 baseline │ C2 rag │ C3 agent │ C4 agent_faults
            │                └─ tools.py search_docs, lookup_ticket ─ faults.py
            └─ scorers.py   taskbench_scorer (+ optional LLM judge)
                     │            └─ metrics.py (pure scoring rules)
                     ▼
          Inspect AI eval()  ──►  logs/<run_id>/*.eval   (raw, git-ignored)
                     │
                     ▼
          report.py  ──►  results/runs/<run_id>/results.jsonl  (one ResultRow per sample × epoch)
                     │
                     ▼
          stats.py + figures.py ──► summary.md, figures/
          calibration.py        ──► label_sheet.jsonl, calibration.md
          manifest.py           ──► manifest.json
```

## Modules

| Module | Responsibility | Needs Inspect? |
|---|---|---|
| `schema.py` | Pydantic models for passages, tickets, tasks, result rows, human labels. Unknown fields are rejected. | No |
| `config.py` | Loads `benchmark.yaml` and `prices.yaml`; checks counts and config names; `token_cost()`. | No |
| `corpus.py` | Turns docs pages into passages with stable IDs. | No |
| `dataset.py` | Loads tasks and corpora; `validate_dataset()` holds every dataset rule. | No |
| `retrieval.py` | BM25 index with deterministic tie-breaking. | No |
| `metrics.py` | Text normalisation, keyword matching, success rule, abstention, citations, recall, conflict and injection checks. | No |
| `faults.py` | Seeded decision whether a tool call fails. | No |
| `make_tickets.py` | Builds and reads the read-only SQLite ticket database. | No |
| `tools.py` | Inspect tools `search_docs` and `lookup_ticket`; records retrieval, faults and exposure in the sample store. | Yes |
| `solvers.py` | Prompts (versioned) and the four solver chains. | Yes |
| `scorers.py` | Wraps `metrics.py` as an Inspect scorer; optional judge. | Yes |
| `tasks.py` | Builds an Inspect `Task` for one configuration, split and condition. | Yes |
| `report.py` | Converts log samples into `ResultRow`s; failures become rows, never gaps. | Only to read logs |
| `stats.py` | Rates with task-clustered bootstrap intervals, paired comparisons, Markdown summary. | No |
| `calibration.py` | Blind label sheet, Cohen's kappa, scorer agreement. | No |
| `manifest.py` | Records git state, versions, hashes and settings for each run. | No |
| `figures.py` | Success-vs-tokens chart. | No |
| `run.py` | The `taskbench` CLI. | Only for `run` and `report` |

Keeping the scoring rules, statistics and dataset checks free of Inspect means they are fully unit tested in milliseconds, and an Inspect upgrade can only break the thin wrappers, which the smoke tests cover.

## Per-sample state

Tools and solvers write to Inspect's sample `store`, which is saved in the log:

| Key | Written by | Used for |
|---|---|---|
| `sample_key` | `init_sample` | `"<task id>:<epoch>"`, seeds fault decisions |
| `retrieved_ids` | RAG solver, `search_docs` | Retrieval recall, injection exposure |
| `injection_exposed` | `record_retrieval` | Denominator of injection resistance |
| `injected_faults` | `_maybe_fault` | Recovery rate; excluded from real tool errors |
| `tool_call_index` | `_maybe_fault` | Makes each call's fault decision unique and reproducible |

## Error handling

- **Tool errors** (missing ticket) are raised as `ToolError`; Inspect returns them to the model as an error message and the run continues.
- **Injected faults** raise `TimeoutError`, which Inspect reports as a `timeout` tool error. They are counted separately from real errors.
- **Argument errors** (the model calls a tool with bad arguments) are Inspect `parsing` errors and count against tool-call validity.
- **Sample errors and limits** do not stop the eval (`fail_on_error=False`). `report.py` writes them as rows with status `error` or `limit_reached` and `success: false`.
- **The agent loop** is bounded by `message_limit` (12) and `time_limit_s` (300).

## Swapping models

The model is any Inspect model string: `--model ollama/llama3.2`, `--model openai/gpt-4o-mini`, or `mockllm/model` for tests. The judge is a separate `grader` model role (`--judge-model`) and must differ from the model under test.

## What v0.1 deliberately leaves out

There is no plugin system, no vector database, no async job queue and no web dashboard. Four configurations are four branches in `build_solver`; adding a fifth means adding one branch and one config name. Abstraction gets added when a second real use appears, not before.
