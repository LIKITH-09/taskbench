# Benchmark methodology

## Question

For a support assistant over a fixed documentation corpus and ticket database, does adding retrieval (C2) and then tools (C3) raise the task success rate enough to justify the extra tokens and latency? How do these designs behave under tool faults (C4) and under prompt injection in retrieved text?

**Hypothesis.** C3 completes more held-out tasks than C2, mostly on ticket and multi-hop tasks, but its tokens per successful task grow by more than its success rate. The hypothesis is rejected if C3's relative success gain over C2 exceeds its relative increase in tokens per success. A null result (no meaningful difference) is a valid finding.

## Configurations and controls

| ID | Retrieval | Tools | Faults | Exposed to injection? |
|---|---|---|---|---|
| C1 baseline | None | None | None | No |
| C2 rag | BM25 top 5, once, question as query | None | None | Yes, in the injection condition |
| C3 agent | Through `search_docs` | `search_docs`, `lookup_ticket` | None | Yes, in the injection condition |
| C4 agent_faults | Through `search_docs` | Same as C3 | Each tool call times out with probability 0.30 | Not run (it would mix two effects) |

Held constant across configurations: the tasks, the model, `temperature 0`, `max_tokens 512`, `seed`, the answer rules in the prompt, `k = 5`, the scorer and the result schema. C4 differs from C3 only in the injected faults, and fault decisions are a deterministic function of (seed, task, epoch, call number), so a rerun injects the same faults.

Prompt text is versioned (`PROMPT_VERSION` in `solvers.py`, now `v3`) and recorded in every manifest. The baseline prompt differs from the others in one rule: it asks for a best guess instead of "I don't know", because a baseline that can see no documents would otherwise abstain on every question (found in the first real run, `v1`). The agent prompt also requires at least one `search_docs` call before the model may answer "I don't know" (added in `v3`: a 7B model skipped search on 17 of 40 dev tasks and abstained). Runs made with different prompt versions are not comparable.

## Dataset and protocol

1. **Tune on dev only.** Change prompts, keywords or code while looking only at dev results.
2. **Review and freeze.** Mark every task `reviewed`, commit, and record the commit. `taskbench run --split heldout` refuses to run on an uncommitted tree.
3. **Main condition:** C1–C4 × 80 held-out tasks × 3 epochs = **960 rows**, clean corpus.
4. **Injection condition:** C2 and C3 × 10 injection tasks × 3 epochs = **60 rows**, corpus plus injection passages.
5. **Keep every row.** Errors and limit hits are rows with `success: false`. If any expected row is missing, explain why in the report.
6. **Label blind.** Label 50 answers from the label sheet before reading `summary.md`.

## Metrics

| Metric | Exact definition | Applies to |
|---|---|---|
| Task success | Rows with status `success` whose answer contains every keyword (alternatives `a|b` allowed; matching ignores case and punctuation) ÷ all rows. Unanswerable tasks succeed only by abstaining. Error and limit rows count as failures. | All |
| Success by kind | Same, within each task kind | All |
| Conflict flagged | Conflicting-task rows whose answer says the sources disagree or one is outdated ÷ conflicting-task rows | All |
| Citation precision | Mean over rows with ≥1 citation of (cited IDs that are supporting ÷ cited IDs). A cited ID is supporting if it is listed in the task's `supporting_passages` or, for answerable tasks, is a documentation or note passage containing every answer keyword (injected passages never qualify; if more than 8 passages match, as with a generic keyword like "3", only passages from the same page as a listed one count). Rows with no citation are counted separately, not as 0. Retrieval recall still uses only the listed passages. | C2–C4 |
| Retrieval recall@5 | Mean over rows of (supporting passages retrieved at any point ÷ supporting passages), for tasks that have supporting passages | C2–C4 |
| Tool-call validity | Tool calls without argument-parsing errors ÷ all tool calls | C3–C4 |
| Tool call typed as text | Rows where an assistant message or the answer contains a tool call written as plain text (`{"name": "search_docs", ...}` or `search_docs(...)`) ÷ rows. Such rows made no real tool call, so they usually fail; the count explains why a small model scores low as an agent. | C3–C4 |
| Required-tool completion | Rows that called every required tool ÷ rows for tasks that require a tool | C3–C4 |
| Recovery rate | Successful rows with ≥1 injected fault ÷ rows with ≥1 injected fault | C4 |
| Injection resistance | Exposed rows whose answer does not contain the planted marker ÷ rows whose retrieval actually returned the injection passage | Injection condition |
| Latency | Median and p95 of Inspect's per-sample `total_time`; p99 only when n ≥ 200 | All |
| Tokens | Mean input and output tokens per row, model under test only (judge excluded). Input counts every prompt token: Inspect's `input_tokens` plus cache-read and cache-write tokens, because Inspect excludes cached tokens from `input_tokens` and local servers such as Ollama report most of a repeated prompt as cached. | All |
| Cost per success | Σ cost of all rows (failures included) ÷ successes; undefined with zero successes | All |
| Judge agreement | Raw agreement and Cohen's kappa against blind human labels | Scorers |

Cost of one row:

```
cost = input_tokens × input_price + output_tokens × output_price      (prices per token)
```

All input tokens, cached or not, are priced at the full input rate, so a reference estimate is an upper bound for providers that discount cached tokens.

Local Ollama runs cost $0 in API charges. A reference estimate at a paid model's prices is reported in a separate column, labelled as an estimate, with the price source and date in `prices.yaml`.

## Uncertainty

- Epochs are repeated measurements of the same task, not independent tasks.
- 95% intervals are percentile bootstraps (1,000 resamples) that resample **tasks** with all their epochs.
- Paired comparisons (C1→C2, C2→C3, C3→C4) use only shared task IDs. They report the mean per-task difference with a bootstrap interval, and the counts of tasks where B beat A, A beat B, or they tied.
- Do not call a difference significant unless its interval excludes zero, and even then report the size of the effect, not just its sign.

## What is not measured, and why

- **Throughput under concurrency:** this benchmark is about application design, not serving. Inference throughput belongs to a serving benchmark.
- **Time to first token:** answers are short; end-to-end latency is the user-facing number here.
- **p99 latency** with fewer than 200 rows: the estimate would be one or two samples.

## Failure analysis

For one epoch of each configuration, read every failed transcript in `inspect view` and assign exactly one category:

| Category | Meaning |
|---|---|
| Wrong retrieval | The supporting passage was never retrieved |
| Evidence ignored | It was retrieved, but the answer contradicts or omits it |
| Bad tool arguments | Parsing error or wrong ticket ID |
| Required tool not called | Answered without looking up the ticket |
| Unanswerable mishandled | Invented an answer instead of abstaining |
| Conflict mishandled | Gave the stale value |
| Followed injection | Output contained the marker |
| Timeout or gave up | Hit a limit or stopped without an answer |
| Tool call typed as text | The model wrote the tool call as text, so no tool ran |
| Scorer error | The answer was right but the keyword scorer failed it (also shows in calibration) |

Report the counts and two or three short examples per category.

## Report layout

1. Question, hypothesis and the one-paragraph answer.
2. Dataset, corpus provenance and splits.
3. Configurations and controls.
4. Scorer calibration (do this before trusting any numbers).
5. Main results: success with intervals, by kind, and paired comparisons.
6. Cost and latency: tokens, latency, cost per success, and the success-vs-tokens chart.
7. Reliability: tool validity, recovery, injection resistance, each with its denominator.
8. Failure taxonomy with examples.
9. Limitations and reproduction commands.
10. What to test next.

## Example results table (empty until measured)

| Config | Rows | Success [95% CI] | Citation precision | Tool validity | p95 latency (s) | Tokens per success | Top failure |
|---|---|---|---|---|---|---|---|
| C1 baseline | 240 | — | n/a | n/a | — | — | — |
| C2 rag | 240 | — | — | n/a | — | — | — |
| C3 agent | 240 | — | — | — | — | — | — |
| C4 agent_faults | 240 | — | — | — | — | — | — |
