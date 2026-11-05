# Development notes

After each session add three lines. These notes become your README history and your interview stories.

- **Done:** what changed, with the commit hash
- **Observed:** errors, failures, surprises
- **Decision:** what you chose and why

Never record a benchmark number here that is not backed by a committed run in `results/runs/`.

---

## 2026-10-22: v0.1 implementation

- **Done:** Full pipeline: corpus from Inspect AI docs at `ae59272`, 120 drafted tasks, 4 configurations, scorer, report, statistics, calibration, CLI, tests.
- **Observed:** BM25 with the question as the query retrieves supporting passages with recall@5 = 0.81 over the 75 tasks that have them (deterministic, no model involved). All 10 injection passages and all 10 conflicting notes are retrieved in the top 5 for their questions.
- **Decision:** Inspect AI pinned exactly (0.3.283), because its breaking changes ship as patch releases. Injection is a separate condition on a separate corpus, so the planted passages cannot contaminate the main results. Limit-hit samples count as failures.
