# Dataset

Everything here is committed except `tickets.sqlite`, which `taskbench build-db` rebuilds from `tickets.jsonl`. `taskbench validate` checks every rule on this page.

## Files

| File | Rows | What it is |
|---|---|---|
| `passages.jsonl` | 1,054 | Inspect AI documentation split into citable passages (`P0001`…) |
| `internal_notes.jsonl` | 10 | Synthetic 2023 "team wiki" notes (`N0001`…) that contradict the docs on one fact each |
| `injection_passages.jsonl` | 10 | Synthetic passages (`X0001`…) carrying a malicious instruction and a unique marker; loaded only in the injection condition |
| `tickets.jsonl` | 40 | Fictional support tickets (`TCK-1001`…) served by the `lookup_ticket` tool |
| `tasks.jsonl` | 120 | Benchmark questions with scoring keys |
| `human_labels.jsonl` | 0 for now | Your blind labels, added after the first held-out run |

## Provenance

- **Source:** https://github.com/UKGovernmentBEIS/inspect_ai, `docs/*.qmd` (top-level pages only), commit `ae59272ed3d66499e2d25b6e31b9d59f5b325217` (main on 2026-10-22).
- **Licence:** MIT, copyright UK AI Security Institute. Each passage records its source path, commit and licence.
- **Splitting rules** (`taskbench/corpus.py`): drop YAML front matter; split on Markdown headings outside code fences; window sections into chunks of at most 250 words on paragraph boundaries (oversized tables and code blocks split by line); drop chunks under 15 words; assign IDs in sorted file order.
- **Integrity:** `configs/benchmark.yaml` stores the SHA-256 of `passages.jsonl`. `python scripts/fetch_corpus.py` re-fetches the commit, rebuilds the file and fails if the hash differs.
- **Synthetic files** (internal notes, injection passages, tickets) were written for this benchmark and are released under CC0. They contain no real people, tickets or secrets.

## Task fields

| Field | Meaning |
|---|---|
| `id` | `Q0001`…`Q0120` |
| `split` | `dev` (40) or `heldout` (80) |
| `kind` | `single_hop`, `multi_hop`, `conflicting`, `unanswerable`, `tool` |
| `question` | What the model sees |
| `answer_keywords` | All must appear in the answer. `a|b` means either alternative. Matching ignores case, punctuation and `_`/`-` |
| `reference_answer` | Human-readable answer, used by the optional LLM judge and the label sheet |
| `supporting_passages` | Passage IDs that contain the answer |
| `required_tools`, `ticket_ids` | Tools and tickets a correct answer needs |
| `stale_keywords` | For conflicting tasks: the outdated value in the internal note |
| `prompt_injection`, `injection_marker` | Set on the 10 held-out injection tasks |
| `review_status` | `draft` until a person has checked the task, then `reviewed` |

## Composition

| Kind | Total | Dev | Held-out | Notes |
|---|---|---|---|---|
| single_hop | 40 | 13 | 27 | One documentation passage answers it |
| multi_hop | 25 | 9 | 16 | 20 need two passages (no single passage holds all keywords, enforced); 5 need a ticket lookup plus a passage |
| conflicting | 10 | 3 | 7 | The docs and an internal note disagree; success needs the documentation's value |
| unanswerable | 15 | 5 | 10 | 10 ask about features absent from the corpus (checked); 5 ask about tickets that do not exist |
| tool | 30 | 10 | 20 | Answer is only in the ticket database |
| **Total** | **120** | **40** | **80** | 10 held-out single-hop tasks are also injection tasks |

The split is stratified by kind with largest-remainder rounding and seed `20261021`.

## How the tasks were drafted

`scripts/draft_tasks.py` records exactly how the drafts were produced. Questions and keywords were written with an LLM's help against passages located by regular expression. The script refuses to write the dataset unless:

- every pattern matches a real passage, so supporting IDs are genuine;
- every answer keyword occurs in the supporting passages;
- no single passage of a two-passage multi-hop task holds all of its keywords;
- the term behind each unanswerable documentation question is absent from the corpus;
- each injection passage is retrieved in the top 5 for its question (measured: 10 of 10), and each conflicting note is retrieved for its question (measured: 10 of 10).

Re-running the script reproduces `tasks.jsonl` byte for byte.

## Review procedure (required before held-out runs)

**Shortcut:** `python scripts/review_tasks.py --split heldout` walks through every draft task, shows the question, keywords and evidence, and lets you accept (`a`), flag (`f`, saved to `data/review_flags.jsonl`), skip (`s`) or quit (`q`). Progress is saved after every task. The checklist below is what to look for. Once tasks are marked reviewed, re-running `scripts/draft_tasks.py` no longer reproduces `tasks.jsonl` byte for byte (it would reset the status), so do not re-run it after reviewing.

For each task in `tasks.jsonl`:

1. Read the question as a user would. Is it clear, and does it have one correct answer?
2. Open each supporting passage (`grep '"P0375"' data/passages.jsonl`) and confirm it really answers the question.
3. Check that the keywords are what a correct answer must contain, and are not so loose that a wrong answer passes. Add `|` alternatives for legitimate phrasings.
4. Set `review_status` to `"reviewed"`, or fix or replace the task.

Change tasks only before the held-out freeze. Record every change in `NOTES.md`. If you edit tasks by hand rather than through the script, keep the counts in `configs/benchmark.yaml` in sync; `taskbench validate` will tell you if they drift.

## Human labels

**Shortcut:** after `taskbench label-sheet --run-id <id>`, run `python scripts/label_answers.py --run-id <id> --labeler YOUR-NAME`. It shows each answer blind, asks `c`orrect / `i`ncorrect / `s`kip, and saves `data/human_labels.jsonl` after every answer. Do it before reading `summary.md`.

After the first held-out run, `taskbench label-sheet --run-id <id>` writes 50 answers to `results/runs/<id>/label_sheet.jsonl` without their automatic scores. Fill in `label` (`correct` or `incorrect`) and `labeler` **before** looking at `summary.md`, then save the rows to `data/human_labels.jsonl` and run `taskbench calibrate --run-id <id>`.
