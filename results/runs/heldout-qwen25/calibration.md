# Scorer calibration: run `heldout-qwen25`

Human labels: 50 (50 matched to result rows).

| Scorer | n | Agreement | Cohen's kappa |
|---|---|---|---|
| Deterministic keyword scorer | 50 | 0.920 | 0.840 |
| LLM judge | 0 | — | — |

## Disagreements with the deterministic scorer

- agent_faults/Q0077/e1: human=correct, deterministic=incorrect
- agent/Q0077/e2: human=correct, deterministic=incorrect
- agent_faults/Q0077/e2: human=correct, deterministic=incorrect
- agent/Q0084/e2: human=correct, deterministic=incorrect
