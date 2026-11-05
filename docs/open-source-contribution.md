# Upstream contribution: Inspect AI

TaskBench is built on Inspect AI, so problems you hit while building it are real upstream problems. That is the honest route to a contribution: find a bug through use, reproduce it, and fix it only when maintainers want the fix.

## Inspect AI's policy for outside contributors (read this first)

Inspect AI's `AGENTS.md` and `CONTRIBUTING.md` (main branch, checked 2026-10-22) set rules that change how you should approach a PR:

1. **Accepted issue first.** Unless you are on their qualified-contributor roster, every non-trivial PR needs a linked issue that a maintainer has labelled `accepted`. PRs without one are closed automatically. Post your reproduction on the issue and wait.
2. **No `deferred` issues.** Issues labelled `deferred` will not be prioritised; PRs against them are closed.
3. **No duplicates.** If a PR already addresses the issue, comment there instead of opening a competing one.
4. **Trivial docs fixes** (docs-only, under 25 lines) may be opened directly.
5. **New features go in extensions,** not core, unless an accepted issue says otherwise.
6. **Evidence required:** a reproduction or failing test.
7. **AI assistance must be disclosed.** If an AI tool helped, fill in the `### Agent review` section of the PR template and describe honestly what was reviewed. If you comment on someone else's issue with AI help, say so.
8. **Before opening:** run `make check` and `make test`, run at least one fresh-context code review pass, one issue per PR, no `# noqa` or `# type: ignore` without a reason, and never edit `CHANGELOG.md`.
9. **PR title** uses Conventional Commits and states the user-facing outcome, for example `fix: eval_set reuses results after the scorer changes`.

Re-read both files on the day you contribute; they change.

## Candidate issues (checked 2026-10-21; re-check before acting)

| Issue | Problem | Files | Fit |
|---|---|---|---|
| [#5655](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5655) | `eval_set` can return a previous result after only the scorer changed | `_eval/evalset.py` (`task_identifier`) | Best: silent stale scores are an evaluation-correctness bug |
| [#5863](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5863) | `score(action="append")` names the new score differently on errored samples | `_eval/score.py` | Small and concrete |
| [vllm-project/guidellm #602](https://github.com/vllm-project/guidellm/issues/602) | Throughput percentiles misrepresent concurrent runs | `schemas/statistics.py` | Backup; needs statistical justification |

On 2026-10-21 both Inspect issues were open, with no maintainer reply shown, and their reporters had offered to fix them. Ask before working on either.

## Workflow

1. Re-open the issue: state, labels (`accepted`? `deferred`?), assignee, linked PRs, latest comments.
2. Read `CONTRIBUTING.md` and `AGENTS.md` in full.
3. Clone your fork separately from TaskBench; `pip install -e ".[dev]"`; run one relevant test file to confirm a green baseline.
4. Write a minimal reproduction script using `mockllm/model` with exact versions and expected vs observed output.
5. Trace the code path and write down two possible fixes and their trade-offs.
6. Comment on the issue: reproduction, analysis, the fix options, a question about which direction the maintainers prefer, and whether the original reporter is already working on it. Disclose AI assistance.
7. **Stop until a maintainer accepts the issue and picks a direction.** Maintainers aim to triage within 7 days. Once it is `accepted`, comment to claim it before starting.
8. Then write a regression test that fails before the fix, make the smallest correct change, run `make check` and `make test`, and do a fresh-context review pass.
9. Open the PR from a personal fork with "Allow edits by maintainers" on; fill in the template including `### Agent review`; watch CI and answer review promptly.

A clear reproduction and analysis on an issue is a real contribution even if no PR follows. Never claim a merge, an acceptance or a maintainer's view that has not happened.
