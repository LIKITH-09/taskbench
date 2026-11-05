# Roadmap

The implementation of v0.1 is done. What remains is the experiment, and that can't be skipped or automated. The detailed day-by-day plan is in the separate workflow document; this is the checklist.

## Before held-out runs

- [x] Name decided: keep "TaskBench" with a disambiguation note in the README (it differs from the NeurIPS 2024 benchmark of the same name)
- [ ] `pip install -e ".[dev,ollama]"`, then `pytest` passes, including the Inspect smoke tests
- [ ] `uv lock` (or `pip freeze > requirements-lock.txt`) committed
- [x] Review all 120 tasks; every task `review_status: "reviewed"`
- [ ] Dev runs with the local model; prompts tuned on dev only; `PROMPT_VERSION` bumped on every prompt change
- [ ] Optional: a price filled in `prices.yaml` (with source and date) for reference cost estimates
- [ ] Optional: a judge model set in `benchmark.yaml` (different from the model under test)
- [ ] Everything committed: the freeze point

## The experiment

- [ ] Main condition: 960 rows, or every missing row explained
- [ ] Injection condition: 60 rows
- [ ] 50 blind labels, then `taskbench calibrate`
- [ ] Failure taxonomy from one epoch per configuration
- [ ] `results/report.md` written in the layout from the methodology, with limitations
- [ ] Fresh clone reproduces the mock smoke run from the README

## Upstream

- [ ] Issue re-checked; reproduction posted; AI assistance disclosed
- [ ] PR only after a maintainer accepts the issue

## Later (one at a time, each its own small experiment)

- Hybrid BM25 + embedding retrieval: does recall@5 rise, and does success follow?
- A second model: does the ranking of configurations hold?
- A second corpus: does the finding generalise beyond Inspect's docs?
- Trace export to an observability tool, only if a concrete question needs it
