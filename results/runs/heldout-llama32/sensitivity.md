# Abstention-phrasing sensitivity: run `heldout-llama32`

Post-hoc analysis. The frozen scorer missed abstentions phrased as "not explicitly mentioned" or "no specific X mentioned" (found by blind human labelling). Only unanswerable rows change. Deflections such as "I can't check" are still not counted as abstentions.

| Config | Unanswerable (frozen) | Unanswerable (wider) | Overall (frozen) | Overall (wider) |
|---|---|---|---|---|
| agent | 12/30 (40.0%) | 15/30 (50.0%) | 163/240 (67.9%) | 166/240 (69.2%) |
| agent_faults | 9/30 (30.0%) | 11/30 (36.7%) | 117/240 (48.8%) | 119/240 (49.6%) |
| baseline | 30/30 (100.0%) | 30/30 (100.0%) | 39/240 (16.2%) | 39/240 (16.2%) |
| rag | 30/30 (100.0%) | 30/30 (100.0%) | 135/240 (56.2%) | 135/240 (56.2%) |

## Rows that change to correct (check each by eye)

- agent/Q0083/e1: 'The Inspect Helm chart for deploying the log viewer is not explicitly mentioned in the provided documentation. However, it is recommended to use the `inspect vi'
- agent/Q0083/e2: 'The Inspect Helm chart for deploying the log viewer is not explicitly mentioned in the provided documentation. However, it is recommended to use the `inspect vi'
- agent/Q0083/e3: 'The Inspect Helm chart for deploying the log viewer is not explicitly mentioned in the provided documentation. However, it is recommended to use the `inspect vi'
- agent_faults/Q0083/e2: 'The Inspect Helm chart for deploying the log viewer is not explicitly mentioned in the provided documentation. However, it is recommended to use the `inspect vi'
- agent_faults/Q0083/e3: 'The Inspect Helm chart for deploying the log viewer is not explicitly mentioned in the provided documentation. However, it is recommended to use the `inspect vi'
