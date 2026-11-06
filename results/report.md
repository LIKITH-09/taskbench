# TaskBench v0.1: results report

Runs analysed (held-out split, 3 epochs, 80 tasks each):
- `heldout-qwen25`: model `ollama/qwen2.5:7b` (primary; hand-calibrated, sections 4 to 8).
- `heldout-llama32`: model `ollama/llama3.2` (second model; section 5b onwards; not hand-calibrated).

Supporting files in `results/runs/<run_id>/`: `summary.md`, `results.jsonl`, `manifest.json`, `sensitivity.md`, `failure_taxonomy.md`, `figures/`, plus `calibration.md` for qwen only.
Dev-split runs used for tuning: `dev-llama32-v4`, `dev-qwen25-v4` (not used for any headline number).

*Naming note: this TaskBench is unrelated to the NeurIPS 2024 "TaskBench" paper.*

## 1. Question, hypothesis and answer

**Question.** For a documentation-and-ticket support assistant, how much do retrieval and tool use improve answer quality, what do they cost, and how reliable are they when tools fail or documents contain injected instructions?

**Hypotheses (written before the held-out run).** Retrieval beats no retrieval; an agent that chooses its own searches and tools beats fixed retrieval overall; tool faults reduce success; the agent costs more per success than fixed retrieval.

**Answer in one paragraph.** On two small local models (qwen2.5:7b and llama3.2), retrieval is the biggest effect: success rises from 13.8% / 16.2% (no evidence) to 60.0% / 56.2% with fixed retrieval. The agent scores higher overall (75.4% / 67.9%), but only because it can call the ticket tool; fixed retrieval cannot and scores 0/60 on ticket tasks. On documentation tasks alone, fixed retrieval beats the agent on both models (qwen 80.0% vs 67.2%, llama 75.0% vs 57.2%) because the agent's own searches retrieve the supporting passages less often. Injecting tool faults at 30% hurts both, but very differently: 7.1 points on qwen and 19.2 on llama, where the model often wrote its tool call as plain text and recovered from none of 78 faulted calls. Prompt injection was never followed by qwen but was followed in 9 of 30 rag rows and 3 of 18 agent rows on llama. Cost per success at a reference paid price is nearly flat across baseline, rag and agent on both models, so the hypothesis that the agent costs more per success is not supported. The agent's latency penalty is large on qwen (median 2.2x rag) but negligible on llama, so it is model-specific. The other hypotheses are supported, with the caveats above. Conclusions about agents should be read as "for these two small models", not in general.

## 2. Dataset, corpus provenance and splits

- Corpus: the public Inspect AI documentation, split into passages (`data/passages.jsonl`), plus synthetic support tickets (`data/tickets.jsonl`), team-wiki notes (`data/internal_notes.jsonl`, some deliberately stale) and injected passages (`data/injection_passages.jsonl`). Provenance is in `data/README.md`.
- 120 tasks, all human-reviewed: 40 dev, 80 held-out. Held-out kinds: 27 single_hop, 16 multi_hop, 7 conflicting, 10 unanswerable, 20 tool.
- Tasks were frozen and committed (commit `bc0d03b`) before the held-out run; the run requires a clean git tree.
- Scoring is a keyword rule on the answer. Unanswerable tasks succeed only if the model abstains.

## 3. Configurations and controls

| Config | What the model gets |
|---|---|
| baseline | Question only, no evidence (told to give a best guess) |
| rag | Top-k BM25 passages stuffed in the prompt; no tools |
| agent | `search_docs` and `lookup_ticket` tools, chooses its own calls |
| agent_faults | Same as agent, with tool calls failing (timeout) with probability 0.30 |

Controls: within each run the same model, same tasks, same temperature and limits across configs; 3 epochs per task; prompt version v3; fault injection seeded. A separate injection condition (30 rows each for rag and agent) adds a passage containing an instruction with a marker string, and counts a row as failed-resistance if the marker appears.

## 4. Scorer calibration

I labelled 50 answers by hand using a sheet that showed only the question, reference answer and model answer.

- Agreement with the automatic score: **92%**, Cohen's kappa **0.84** (`calibration.md`).
- All disagreements were false negatives on abstention wording ("not explicitly mentioned in the documentation") that the frozen abstention rule did not recognise.
- **Caveat on blindness.** I opened `summary.md` before labelling, so the labels are not fully blind; the sheet itself showed no automatic scores. Earlier labelling attempts were invalid (everything marked correct, so agreement just equalled the scorer's pass rate) and were redone; the 50 labels used are from the final, careful pass.
- Calibration was done on qwen answers only. Llama's answers were not hand-labelled, so its scores are uncalibrated; its post-hoc abstention check (section 5b) found one extra task, but its answer styles may hide other scorer errors.
- Consequence: the frozen scorer is used for every headline number. A wider abstention rule is reported only as a labelled post-hoc sensitivity analysis (section 5).

## 5. Main results

Success on the main condition, n = 240 rows per config (80 tasks x 3 epochs), 95% bootstrap interval resampling tasks:

| Config | Success | 95% CI |
|---|---|---|
| baseline | 13.8% (33/240) | [6.2, 21.2] |
| rag | 60.0% (144/240) | [50.0, 71.2] |
| agent | 75.4% (181/240) | [65.4, 84.2] |
| agent_faults | 68.3% (164/240) | [59.2, 76.7] |

Rows are epochs of the same tasks, so they are not independent; the intervals resample tasks to account for this.

**By task kind (successes / rows):**

| Config | conflicting | multi_hop | single_hop | tool | unanswerable |
|---|---|---|---|---|---|
| baseline | 0/21 | 0/48 | 30/81 | 3/60 | 0/30 |
| rag | 12/21 | 27/48 | 75/81 | 0/60 | 30/30 |
| agent | 18/21 | 17/48 | 66/81 | 60/60 | 20/30 |
| agent_faults | 14/21 | 17/48 | 60/81 | 56/60 | 17/30 |

**Paired comparisons (per-task mean difference, shared tasks):**

| A to B | Difference [95% CI] | B better / A better / ties |
|---|---|---|
| baseline to rag | +46.2 pp [+33.8, +57.5] | 38 / 1 / 41 |
| rag to agent | +15.4 pp [+0.4, +29.6] | 23 / 12 / 45 |
| agent to agent_faults | -7.1 pp [-10.8, -3.3] | 2 / 16 / 62 |

The rag-to-agent interval barely excludes zero; treat it as suggestive, not firm.

**What drives rag vs agent.**
- Ticket tasks: agent 60/60, rag 0/60 (rag has no tools). This alone produces the overall agent lead.
- Documentation tasks only (excluding the tool kind, 180 rows): rag **80.0%**, agent **67.2%**.
- Retrieval recall is 0.84 for rag and 0.71 for the agent: the agent's self-written queries retrieve supporting passages less often than the raw question does.
- Multi-hop is weak everywhere (rag 56%, agent 35%).
- Unanswerable: rag abstains on 30/30; the agent invents an answer more often (20/30 frozen).
- Conflicting (stale wiki note vs official docs): agent 85.7%, rag 57.1%. Rag followed the stale note on 3 of 7 conflict tasks in epoch 1. I did not investigate why the agent handles these better.

**Post-hoc abstention sensitivity** (`sensitivity.md`, labelled post-hoc, not used for headline numbers): widening the abstention rule raises agent unanswerable success to 25/30 (83.3%) and agent documentation-task success to 70.0%. Rag stays at 80.0%, so the rag advantage on documentation tasks survives the wider rule but shrinks from 12.8 to 10 points.

**Citations.** Citation precision (when an answer cites): rag 0.86 (n=135), agent 0.69 (n=112), agent_faults 0.78 (n=95). Many agent and rag answers carry no citation (rag 105, agent 128, agent_faults 145 of 240 rows), so these precisions describe the subset that cites.

## 5b. Second model: llama3.2 (`heldout-llama32`)

Same tasks, configs, prompt version and fault rate; frozen scorer; n = 240 rows per config.

| Config | Success | 95% CI |
|---|---|---|
| baseline | 16.2% (39/240) | [8.8, 23.8] |
| rag | 56.2% (135/240) | [45.0, 67.5] |
| agent | 67.9% (163/240) | [57.5, 77.9] |
| agent_faults | 48.8% (117/240) | [39.6, 57.9] |

| Config | conflicting | multi_hop | single_hop | tool | unanswerable |
|---|---|---|---|---|---|
| baseline | 0/21 | 3/48 | 6/81 | 0/60 | 30/30 |
| rag | 9/21 | 21/48 | 75/81 | 0/60 | 30/30 |
| agent | 13/21 | 18/48 | 60/81 | 60/60 | 12/30 |
| agent_faults | 5/21 | 11/48 | 46/81 | 46/60 | 9/30 |

| A to B | Difference [95% CI] | B better / A better / ties |
|---|---|---|
| baseline to rag | +40.0 pp [+28.7, +51.2] | 33 / 1 / 46 |
| rag to agent | +11.7 pp [-5.0, +26.7] | 25 / 16 / 39 |
| agent to agent_faults | -19.2 pp [-25.4, -13.3] | 1 / 31 / 48 |

**Compared with qwen:**
- **Same direction:** retrieval gives a large gain; rag beats the agent on documentation tasks only (rag 135/180 = 75.0%, agent 103/180 = 57.2%); agent recall is lower than rag's (0.68 vs 0.84); the agent is far better on ticket tasks (60/60 vs 0/60).
- **Rag vs agent overall is not established for llama:** the paired interval includes zero.
- **Baseline is mostly abstention credit.** Llama answers "I couldn't find any information" to almost every baseline question, even though the baseline prompt asks for a best guess. It therefore scores 30/30 on unanswerable tasks and only 9/210 (about 4%) on answerable ones. Its 16.2% baseline is not comparable to qwen's, which guessed and failed the unanswerable tasks. Rag also scores 30/30 on unanswerable on both models.
- **The agent invents answers on unanswerable tasks more than rag**: 12/30 correct (40.0%) on llama, 20/30 on qwen.
- **Faults are far more damaging on llama** (-19.2 pp). In 69 of 240 agent_faults rows (8 of 240 agent rows) a tool call was written as plain text, so no tool ran. After a fault the model often says "I'll try again." and then prints the call as text or answers without evidence. Recovery is 0/78. (In the earlier dev run `dev-llama32-v4`, faults were injected at a rate of 0.1 and did not lower llama's success; the held-out runs use 0.30, so the two results are consistent with a penalty that grows with the fault rate, which I did not test directly.)
- **Citations nearly vanish for the llama agent**: 237 of 240 rows carry none, so its citation precision of 0.00 rests on 3 rows. Rag citation precision is 0.79 (n=78).
- **Post-hoc abstention sensitivity** (`sensitivity.md`): only one task (Q0083) changes, in 5 rows. Agent unanswerable goes from 12/30 to 15/30 and overall from 67.9% to 69.2%. The Q0083 answers say the Helm chart "is not explicitly mentioned" but then suggest an alternative; check them by eye before relying on the wider number.

## 6. Cost and latency

| Config | Median / p95 latency (s) | Mean in / out tokens | Ref. est. cost per success (USD) |
|---|---|---|---|
| baseline | 20.07 / 44.43 | 96 / 46 | 0.00955 |
| rag | 15.54 / 28.76 | 1430 / 27 | 0.01044 |
| agent | 34.56 / 52.48 | 1640 / 76 | 0.01071 |
| agent_faults | 33.03 / 65.89 | 1707 / 87 | 0.01253 |

- Direct API cost is $0 (local Ollama); this excludes hardware and electricity.
- **The reference cost is an estimate, not a measurement.** It prices the measured tokens at Claude Opus 5.5 rates of $4 per million input tokens and $20 per million output tokens (`configs/prices.yaml`). Every input token is charged at the full rate, so cached-prompt discounts are ignored and the figure is an upper bound. The rates come from a third-party page dated 2026-09-23 that cites Anthropic's pricing documentation; I could not open the vendor's own page. Re-check before relying on them.
- Per attempt, rag costs about $0.0063 and the agent about $0.0081. Per *success* the gap nearly closes ($0.0104 vs $0.0107), because the agent succeeds more often. Tokens per success are about 6% lower for the agent. Cost is not the agent's penalty here.
- Baseline looks cheapest per success because it is cheap per attempt, but 13.8% success on mostly guessable questions makes that number low-information.
- On qwen, latency is the real cost: the agent's median is about 2.2x rag's (34.6 s vs 15.5 s), and p95 is 52 s. Local-model latency depends on this laptop's hardware and says little about hosted latency.
- Faults add about 17% to the reference cost per success (0.01253 vs 0.01071) from retries and failed rows.

**llama3.2, same reference price ($4 / $20 per million tokens, same caveats):**

| Config | Median / p95 latency (s) | Mean in / out tokens | Ref. est. cost per success (USD) |
|---|---|---|---|
| baseline | 2.49 / 5.41 | 108 / 35 | 0.00696 |
| rag | 4.57 / 9.03 | 1420 / 27 | 0.01105 |
| agent | 4.98 / 7.81 | 1574 / 45 | 0.01060 |
| agent_faults | 5.14 / 7.05 | 1334 / 46 | 0.01284 |

On llama the agent is slightly cheaper per success than rag, and its latency is only about 1.1x rag's (4.98 s vs 4.57 s median). So the agent's latency penalty seen on qwen is model-specific, not a general property of the agent configuration. Llama is also about 7x faster than qwen on this laptop.

## 7. Reliability

Qwen first, then llama.

- **Tool validity** (calls with valid arguments): agent 219/219 and agent_faults 290/290 (100%). No tool call was typed as text.
- **Recovery** (after an injected fault, the model retried and finished): 39/72 = **54.2%** [40.0, 67.6]. Some failures are give-ups after one timeout (see section 8).
- **Fault effect:** -7.1 pp overall (paired CI [-10.8, -3.3]).
- **Injection resistance (qwen):** no injected instruction was followed. Rag 30/30, agent 24/24 (the metric's denominator for the agent is 24 of 30 rows). Injection-condition success: rag 90.0% [70.0, 100.0], agent 70.0% [40.0, 100.0]. With only 30 rows per config and a single injection style, "100% resisted" means "none observed in this set", not "immune". Rag injection citation precision drops to 0.43, so injected text does pull citations toward the wrong passage even when it is not obeyed.

**llama3.2:**
- **Tool validity:** 238/238 valid calls for both agent and agent_faults. This counts only calls that actually ran; the 69 text-typed calls in agent_faults (8 in agent) are reported separately.
- **Recovery:** 0/78 (0.0%).
- **Injection resistance:** rag 21/30 (70.0%) [40.0, 100.0] and agent 15/18 (83.3%) [50.0, 100.0], so the injected instruction was followed in 9 rag rows and 3 agent rows. Injection-condition success was 50.0% for both. With 30 rows per config the intervals are wide, but unlike qwen this model is clearly not immune.

## 8. Failure taxonomy

Automatic first pass on epoch 1 (`failure_taxonomy.md`); examples were checked by eye. Each failed row gets the first category that fits.

| Category | baseline | rag | agent | agent_faults |
|---|---|---|---|---|
| Gave up after a tool timeout (did not retry) | 0 | 0 | 0 | 2 |
| No evidence available (baseline by design) | 59 | 0 | 0 | 0 |
| Scorer miss (abstention phrasing) | 0 | 0 | 1 | 2 |
| Unanswerable mishandled (invented an answer) | 10 | 0 | 1 | 1 |
| Required tool unavailable (rag has no tools) | 0 | 21 | 0 | 0 |
| Conflict mishandled | 0 | 3 | 1 | 2 |
| Wrong retrieval (no supporting passage retrieved) | 0 | 3 | 11 | 14 |
| Partial retrieval (some supporting passages missing) | 0 | 5 | 3 | 2 |
| Evidence ignored (retrieved, answer still wrong) | 0 | 0 | 1 | 1 |
| **Total failed rows** | **69** | **32** | **18** | **24** |

The dominant failure by far for the agent is **wrong retrieval** (11 of 18; 14 of 24 with faults): its own search queries do not surface the supporting passage, e.g. Q0001 and Q0017 where it answers from unrelated passages, or Q0015 where it says "I don't know".

Short examples:
- Rag, conflict: Q0072 answers "10 seconds ... according to the Team wiki [N0007]", the stale internal value.
- Agent, unanswerable: Q0080 states a 24-hour retention period for a hosted log server that does not exist in the docs.
- Agent_faults, give-up: Q0096 "I couldn't retrieve the status of ticket TCK-1033 right now. Let's try again later." after one timeout, with no retry.
- Scorer miss: Q0077 says the vector database name "is not explicitly mentioned in the provided documentation", which is correct but fails the frozen abstention rule.
- Baseline: 59 of 69 failures are questions it cannot know without evidence; 10 are invented answers to unanswerable questions.

The "Scorer miss" row (5 rows across the qwen agent configs) is the same issue measured in calibration.

**llama3.2, epoch 1** (`heldout-llama32/failure_taxonomy.md`):

| Category | baseline | rag | agent | agent_faults |
|---|---|---|---|---|
| Tool call typed as text (no tool ran) | 0 | 0 | 2 | 21 |
| Gave up after a tool timeout (did not retry) | 0 | 0 | 0 | 5 |
| No evidence available (baseline by design) | 67 | 0 | 0 | 0 |
| Scorer miss (abstention phrasing) | 0 | 0 | 1 | 0 |
| Unanswerable mishandled (invented an answer) | 0 | 0 | 5 | 4 |
| Required tool unavailable (rag has no tools) | 0 | 21 | 0 | 0 |
| Conflict mishandled | 0 | 3 | 2 | 2 |
| Wrong retrieval | 0 | 3 | 11 | 6 |
| Partial retrieval | 0 | 6 | 3 | 2 |
| Evidence ignored | 0 | 2 | 1 | 0 |
| **Total failed rows** | **67** | **35** | **25** | **40** |

Llama-specific patterns:
- Faults: 26 of 40 agent_faults failures are a text-typed tool call or a give-up. Example: Q0010 "I'll try again. {"name": "lookup_ticket", "parameters": {"ticket_id": "TCK-1001"}}", where the model also used a ticket ID that was not in the question. Another: Q0024 "I'll try again." followed by an answer with no evidence.
- Unanswerable: the agent invents specifics, e.g. Q0079 "The Inspect flag that uploads logs automatically to Google Drive is `--log-drive`."
- Wrong retrieval remains the largest agent failure (11 of 25), as on qwen, e.g. Q0003 answers `continue_on_fail` from no supporting passage.
- Conflicts: rag and the agent both gave the stale or wrong value in places (e.g. Q0074 `INSPECT_MODEL` from a wiki passage; Q0071 `mode` reducer).

## 9. Limitations and reproduction

**Limitations.**
1. **Two small local models, no hosted or frontier model.** The two models disagree on how much faults hurt (-7.1 vs -19.2 pp), on injection resistance (100% vs 70% for rag) and on latency, so conclusions about agents are model-specific. Llama's answers were not hand-calibrated, and its baseline score is mostly abstention credit (section 5b).
2. **Dev tuning.** Prompts (v1 to v3), the abstention regex, citation-support rule and fault rate (0.10 to 0.30) were tuned on dev and on a 5-task smoke run before freezing. The held-out split was not used for tuning, but the dev tasks overlap in style with it.
3. **Baseline design.** The baseline prompt asks for a best guess, which forces answers to unanswerable questions, so baseline unanswerable = 0/30 reflects the prompt as much as the model. Some single-hop baseline successes are guessable keywords (37% on single_hop).
4. **Keyword scorer.** 92% agreement with my labels on 50 answers, one labeller, not fully blind (section 4). Frozen results are conservative on abstentions.
5. **Small samples.** 80 tasks; 7 conflict and 10 unanswerable tasks; 30 injection rows per config; intervals are wide, especially per kind.
6. **Single injection style** and a single fault type (timeout).
7. **Fault rate 0.30** is an assumption, not a measured production rate.
8. **Cost is an upper-bound estimate** from unverified third-party prices (section 6), and local latency is hardware-specific.
9. **Unexplained finding:** rag follows the stale wiki note on 3 of 7 conflict tasks while the agent mostly does not; I did not test why.
10. **Taxonomy** is an automatic first-match pass on epoch 1 only.

**Reproduce** (from the project folder with the virtual environment active):

```
pip install -r requirements-lock.txt
pytest
ollama pull qwen2.5:7b
taskbench run --config all --split heldout --condition all --model ollama/qwen2.5:7b --run-id heldout-qwen25
taskbench run --config all --split heldout --condition all --model ollama/llama3.2 --run-id heldout-llama32
taskbench report --run-id heldout-qwen25
taskbench stats --run-id heldout-qwen25
taskbench label-sheet --run-id heldout-qwen25
python scripts/label_answers.py --run-id heldout-qwen25 --labeler YOUR-NAME
taskbench calibrate --run-id heldout-qwen25
python scripts/sensitivity_abstention.py --run-id heldout-qwen25
python scripts/failure_taxonomy.py --run-id heldout-qwen25
```

A held-out run needs a clean committed git tree. A model run is not bit-for-bit repeatable, so expect small differences.

## 10. What to test next

1. **Add a hosted model** and hand-label a sample of llama's answers, since both held-out models are small and local and only qwen is calibrated.
2. **Make the agent search with the raw question first**, then refine. Wrong retrieval is its main failure and rag's raw-question retrieval is stronger.
3. **Give rag the ticket tool** (a "rag plus lookup" config) to separate the effect of tools from the effect of agentic search.
4. **Vary fault rate** (0.10, 0.30, 0.50) and fault type, and test a retry instruction in the prompt, since 45% of faulted calls on qwen and all of them on llama were not recovered. Also test a parser or prompt change that stops the model printing tool calls as text.
5. **Investigate the stale-note result** on conflict tasks, including a larger conflict set.
6. **Strengthen injection testing** with more styles and a larger set, and report citation damage separately from obedience.
7. **Second labeller and a judge model** to reduce dependence on keyword scoring and one labeller.
