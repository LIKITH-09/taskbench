# Abstention-phrasing sensitivity: run `heldout-qwen25`

Post-hoc analysis. The frozen scorer missed abstentions phrased as "not explicitly mentioned" or "no specific X mentioned" (found by blind human labelling). Only unanswerable rows change. Deflections such as "I can't check" are still not counted as abstentions.

| Config | Unanswerable (frozen) | Unanswerable (wider) | Overall (frozen) | Overall (wider) |
|---|---|---|---|---|
| agent | 20/30 (66.7%) | 25/30 (83.3%) | 181/240 (75.4%) | 186/240 (77.5%) |
| agent_faults | 17/30 (56.7%) | 22/30 (73.3%) | 164/240 (68.3%) | 169/240 (70.4%) |
| baseline | 0/30 (0.0%) | 0/30 (0.0%) | 33/240 (13.8%) | 33/240 (13.8%) |
| rag | 30/30 (100.0%) | 30/30 (100.0%) | 144/240 (60.0%) | 144/240 (60.0%) |

## Rows that change to correct (check each by eye)

- agent/Q0077/e1: "The name of Inspect's built-in vector database for retrieval is not explicitly mentioned in the provided documentation. However, the documentation does discuss "
- agent/Q0077/e2: "The name of Inspect's built-in vector database for retrieval is not explicitly mentioned in the provided documentation. However, the documentation does discuss "
- agent/Q0084/e2: 'Based on the documentation, there is no specific command mentioned for creating a Jira issue from a failed sample. The `inspect ctl sample requeue` command can '
- agent/Q0077/e3: "The name of Inspect's built-in vector database for retrieval is not explicitly mentioned in the provided documentation. However, the documentation does discuss "
- agent/Q0084/e3: 'Based on the documentation, there is no specific command mentioned for creating a Jira issue from a failed sample. The `inspect ctl sample requeue` command can '
- agent_faults/Q0077/e1: "The name of Inspect's built-in vector database for retrieval is not explicitly mentioned in the provided documentation. However, the documentation does discuss "
- agent_faults/Q0080/e1: "The default retention period for logs in Inspect's hosted log server is not explicitly stated in the documentation. However, for image logging, by default, inli"
- agent_faults/Q0077/e2: "The name of Inspect's built-in vector database for retrieval is not explicitly mentioned in the provided documentation. However, the documentation does discuss "
- agent_faults/Q0077/e3: "The name of Inspect's built-in vector database for retrieval is not explicitly mentioned in the provided documentation. However, the documentation does discuss "
- agent_faults/Q0084/e3: 'Based on the documentation, there is no specific command mentioned for creating a Jira issue from a failed sample. The closest related command is `inspect ctl s'
