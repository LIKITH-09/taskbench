# Failure categories: run `heldout-llama32`, epoch 1

Automatic first pass: each failed main-condition row gets the first category that fits. Verify the examples by eye before quoting them.

| Category | baseline | rag | agent | agent_faults |
|---|---|---|---|---|
| Tool call typed as text (no tool ran) | 0 | 0 | 2 | 21 |
| Gave up after a tool timeout (did not retry) | 0 | 0 | 0 | 5 |
| No evidence available (baseline by design) | 67 | 0 | 0 | 0 |
| Scorer miss (abstention phrasing) | 0 | 0 | 1 | 0 |
| Unanswerable mishandled (invented an answer) | 0 | 0 | 5 | 4 |
| Required tool unavailable (rag has no tools) | 0 | 21 | 0 | 0 |
| Conflict mishandled | 0 | 3 | 2 | 2 |
| Wrong retrieval (no supporting passage retrieved) | 0 | 3 | 11 | 6 |
| Partial retrieval (some supporting passages missing) | 0 | 6 | 3 | 2 |
| Evidence ignored (retrieved, answer still wrong or missing) | 0 | 2 | 1 | 0 |
| **Total failed rows** | **67** | **35** | **25** | **40** |

## Examples

### baseline: No evidence available (baseline by design)
- Q0001 (single_hop): "I couldn't find any information on an environment variable that sets the global default log file format for Inspect."
- Q0002 (single_hop): "I'm not aware of the specific command-line options for INSPECT_EVAL_MODEL. However, I can suggest that you may need to pass the --no-model option or a similar flag to override the model evaluation."
- Q0003 (single_hop): "I'm not aware of the specific Task option that allows an evaluation to tolerate a proportion of sample errors before the whole eval fails."

### rag: Required tool unavailable (rag has no tools)
- Q0064 (multi_hop): "I don't know."
- Q0092 (tool): "I don't know."
- Q0093 (tool): "I don't know."

### rag: Conflict mishandled
- Q0070 (conflicting): 'The environment variable `INSPECT_LOGS_PATH` overrides the default `./logs` log directory. [P0263]'
- Q0071 (conflicting): 'The mode reducer combines epoch scores into one score by default. [P0462]'
- Q0074 (conflicting): 'According to [P0123] Team wiki (2023), you can set the environment variable `INSPECT_MODEL` to select the model, so you do not need to pass `--model`.'

### rag: Wrong retrieval (no supporting passage retrieved)
- Q0002 (single_hop): 'You pass the `--model-spec` argument with an empty mapping, like this:  ```bash inspect eval arc.py --model-spec \'{}\' ```  Or, using the `eval()` function:  ```python eval("arc.py", model={}) ```  Thi'
- Q0017 (single_hop): "I don't know."
- Q0041 (multi_hop): 'The `FieldSpec` class maps non-standard dataset fields onto samples. The CLI option to shuffle samples is `--shuffle`.'

### rag: Partial retrieval (some supporting passages missing)
- Q0043 (multi_hop): 'The function that connects to a local MCP server is `mcp_server_local()`, but the passage does not mention this function. However, [P0063] mentions that using `execution="local"` allows the server\'s t'
- Q0054 (multi_hop): 'The CLI flag that disables epoch reducers is `--no-epochs-reducer`.   The Task option that tolerates a share of sample errors is `epochs=Epochs(n, reducer)`, where `n` is an integer epoch override, or'
- Q0055 (multi_hop): 'According to [P0342] Model APIs > Filtering Model Call Data, `response_schema` takes a `ResponseSchema` object, which includes a `json_schema` field that takes a function, such as `json_schema()`, to '

### rag: Evidence ignored (retrieved, answer still wrong or missing)
- Q0056 (multi_hop): 'According to [P0226] Datasets > Sample Setup, the `setup` field contains either a path to a bash setup script (resolved relative to the dataset path) or the contents of a script to execute. Setup scri'
- Q0072 (conflicting): 'According to [P0302], with `--no-retry-immediate`, the default `--retry-wait` is not explicitly stated. However, it is mentioned that the default retry wait between attempts is 10 seconds when `--no-r'

### agent: Tool call typed as text (no tool ran)
- Q0043 (multi_hop): 'I\'ll try again with a different ticket ID.  {"name": "lookup_ticket", "parameters": {"ticket_id":"TCK-1001"}}'
- Q0055 (multi_hop): '{"name":"response_schema","parameters":{}}   {"name":"lookup_ticket","parameters":{"ticket_id":"TCK-1001"}}'

### agent: Scorer miss (abstention phrasing)
- Q0083 (unanswerable): 'The Inspect Helm chart for deploying the log viewer is not explicitly mentioned in the provided documentation. However, it is recommended to use the `inspect view bundle` command to create a self-cont'

### agent: Unanswerable mishandled (invented an answer)
- Q0076 (unanswerable): 'The `inspect log export-config` command exports a run config YAML from a log file, which can then be used to reproduce the run using the `inspect eval --run-config` command.'
- Q0077 (unanswerable): 'The Inspect AI built-in vector database for retrieval is called the `model database` [P0113].'
- Q0079 (unanswerable): 'The Inspect flag that uploads logs automatically to Google Drive is `--log-drive`.'

### agent: Conflict mishandled
- Q0071 (conflicting): 'The reducer that combines epoch scores into one score by default is the `mode` reducer.'
- Q0072 (conflicting): "I don't know."

### agent: Wrong retrieval (no supporting passage retrieved)
- Q0003 (single_hop): 'The `continue_on_fail` option allows an evaluation to tolerate a proportion of sample errors before the whole eval fails.'
- Q0007 (single_hop): 'Sample IDs are assigned by the `samples_df()` function, which produces a globally unique ID for each sample, contained in the `sample_id` field. This field is also included in the data frames created '
- Q0010 (single_hop): "I don't know."

### agent: Partial retrieval (some supporting passages missing)
- Q0054 (multi_hop): 'The CLI flag that disables epoch reducers is `--no-epochs-reducer`. The Task option that tolerates a share of sample errors is `retry_on_error`.'
- Q0058 (multi_hop): 'The `retry_refusals` generation option retries samples where the model refused to answer or help with the request.   The `fail_on_refusal` generation option fails samples where the model refused to an'
- Q0059 (multi_hop): 'The sandbox agent bridge uses port 8080. The tool wrapper that hands a conversation to another agent is called `handoff()`.'

### agent: Evidence ignored (retrieved, answer still wrong or missing)
- Q0053 (multi_hop): 'The function that computes metrics per metadata group is `grouped()`, and the `stderr()` parameter clusters standard errors.'

### agent_faults: Tool call typed as text (no tool ran)
- Q0010 (single_hop): 'I\'ll try again.   {"name": "lookup_ticket", "parameters": {"ticket_id": "TCK-1001"}}'
- Q0012 (single_hop): 'I\'ll try again.   {"name": "lookup_ticket", "parameters": {"ticket_id": "TCK-1001"}}'
- Q0016 (single_hop): 'I\'ll try again.   {"name": "search_docs", "parameters": {"query": "Inspect Dataset methods subset and reorder"}}'

### agent_faults: Gave up after a tool timeout (did not retry)
- Q0024 (single_hop): "I'll try again.   The `wrap` function in Inspect AI wraps an agent so another agent can hand the conversation off to it."
- Q0035 (single_hop): "I'll try again.   Unfortunately, I don't have enough information to provide a default choice. Let me search the documentation for human_reviewer()."
- Q0074 (conflicting): "I'll try again.   The environment variable that selects the model without needing to pass --model is MODEL. [P0123]"

### agent_faults: Unanswerable mishandled (invented an answer)
- Q0076 (unanswerable): 'The `inspect log export-config` command exports a run config YAML from a log file, which can then be used to reproduce the run using the `inspect eval --run-config` command.'
- Q0077 (unanswerable): 'The Inspect AI built-in vector database for retrieval is called the `model database` [P0113].'
- Q0079 (unanswerable): 'The Inspect flag that uploads logs automatically to Google Drive is `--log-drive`.'

### agent_faults: Conflict mishandled
- Q0071 (conflicting): 'The reducer that combines epoch scores into one score by default is the `mode` reducer.'
- Q0072 (conflicting): "I don't know."

### agent_faults: Wrong retrieval (no supporting passage retrieved)
- Q0003 (single_hop): 'The `continue_on_fail` option allows an evaluation to tolerate a proportion of sample errors before the whole eval fails.'
- Q0007 (single_hop): 'Sample IDs are assigned by the `samples_df()` function, which produces a globally unique ID for each sample, contained in the `sample_id` field. This field is also included in the data frames created '
- Q0037 (single_hop): "I don't know. I couldn't find the completion time for batched generations in the search results. I'll try searching again."

### agent_faults: Partial retrieval (some supporting passages missing)
- Q0054 (multi_hop): 'The CLI flag that disables epoch reducers is `--no-epochs-reducer`. The Task option that tolerates a share of sample errors is `retry_on_error`.'
- Q0058 (multi_hop): 'The `retry_refusals` generation option retries samples where the model refused to answer or help with the request.   The `fail_on_refusal` generation option fails samples where the model refused to an'

