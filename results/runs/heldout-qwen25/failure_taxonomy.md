# Failure categories: run `heldout-qwen25`, epoch 1

Automatic first pass: each failed main-condition row gets the first category that fits. Verify the examples by eye before quoting them.

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
| Evidence ignored (retrieved, answer still wrong or missing) | 0 | 0 | 1 | 1 |
| **Total failed rows** | **69** | **32** | **18** | **24** |

## Examples

### baseline: No evidence available (baseline by design)
- Q0002 (single_hop): 'If you want to run an evaluation without using a model, even though `INSPECT_EVAL_MODEL` is set, you can pass an empty model path or a dummy model path on the command line, such as `--model_path /path'
- Q0003 (single_hop): 'The Task option that allows an evaluation to tolerate a proportion of sample errors before failing is likely the "error tolerance" or "failure threshold" setting. This setting defines how many errors '
- Q0007 (single_hop): 'In the absence of an ID field, the Inspect AI evaluation framework typically generates a unique sample ID for each data point in the dataset, often using a sequential number or a hash based on the dat'

### baseline: Unanswerable mishandled (invented an answer)
- Q0076 (unanswerable): "The `inspect export` command can be used to export evaluation logs, but it typically requires specifying the format and destination. There isn't a direct command to export to Excel, but you can export"
- Q0077 (unanswerable): 'Based on the information available, Inspect AI uses an embedded vector database for retrieval tasks, but the specific name of this database is not publicly disclosed.'
- Q0079 (unanswerable): 'Based on common knowledge, Inspect AI does not have a specific flag for automatically uploading logs to Google Drive. However, such functionality might be available through custom configurations or in'

### rag: Required tool unavailable (rag has no tools)
- Q0064 (multi_hop): "I don't know."
- Q0092 (tool): "I don't know."
- Q0093 (tool): "I don't know."

### rag: Conflict mishandled
- Q0070 (conflicting): 'The environment variable that overrides the default ./logs log directory is INSPECT_LOGS_PATH [N0005].'
- Q0072 (conflicting): 'The default --retry-wait between eval-set attempts is 10 seconds when --no-retry-immediate is set, according to the Team wiki [N0007].'
- Q0074 (conflicting): 'The environment variable that selects the model so you do not need to pass --model is INSPECT_MODEL [N0009].'

### rag: Wrong retrieval (no supporting passage retrieved)
- Q0002 (single_hop): "I don't know."
- Q0017 (single_hop): 'The class that customises how long cached model responses are kept is not explicitly mentioned in the provided passages. However, the `prompt_cache_retention` model arg can be used to override the def'
- Q0041 (multi_hop): 'The `FieldSpec` class maps non-standard dataset fields onto samples [P0405]. The `shuffle()` method can be used to shuffle samples, though it is not a CLI option; it can be called directly on the data'

### rag: Partial retrieval (some supporting passages missing)
- Q0043 (multi_hop): 'The function to connect to a local MCP server is not explicitly named in the provided passages, but it is implied that it would be a function like `mcp_server_local()` based on the pattern of function'
- Q0055 (multi_hop): 'The `response_schema` generation config option takes a `ResponseSchema` object [P0869]. There is no information provided about an object that lists the HTTP requests of the last run [P0869][P0867][P03'
- Q0058 (multi_hop): 'The `retry_refusals` option retries erroring samples [P0366], and the `--fail-on-refusal` flag turns model refusals into sample errors [P0379].'

### agent: Scorer miss (abstention phrasing)
- Q0077 (unanswerable): "The name of Inspect's built-in vector database for retrieval is not explicitly mentioned in the provided documentation. However, the documentation does discuss a model database used for context window"

### agent: Unanswerable mishandled (invented an answer)
- Q0080 (unanswerable): "The default log retention period for Inspect's hosted log server is 24 hours, as indicated in the documentation for prompt caching [P0625]."

### agent: Conflict mishandled
- Q0072 (conflicting): 'The default `--retry-wait` between eval-set attempts when `--no-retry-immediate` is set is 10 seconds, according to the documentation [P0564].'

### agent: Wrong retrieval (no supporting passage retrieved)
- Q0001 (single_hop): 'The environment variable that sets the global default log file format for Inspect is `INSPECT_EVAL_LOG_FORMAT`, which can be configured in your `.env` configuration file. [P0540] [P0445] [P0268] [P029'
- Q0015 (single_hop): "I don't know."
- Q0017 (single_hop): 'The class that customises how long cached model responses are kept is the `AsyncOpenAI` class, through its `prompt_cache_retention` model arg. This arg sets the retention policy for the prompt cache, '

### agent: Partial retrieval (some supporting passages missing)
- Q0041 (multi_hop): 'The `Dataset` class maps non-standard dataset fields onto samples using the `filter()` method. To shuffle samples, you can use the `--sample-shuffle` option in the CLI or the `sample_shuffle` paramete'
- Q0055 (multi_hop): 'The `response_schema` takes a `ResponseSchema` object, as shown in the example from [P0869]:  ```python from inspect_ai.model import ResponseSchema from inspect_ai.util import json_schema  config = Ge'
- Q0059 (multi_hop): 'Based on the provided documentation:  - The sandbox agent bridge uses port 13131 for communication. This is mentioned in the documentation for configuring the sandbox to communicate with the Inspect m'

### agent: Evidence ignored (retrieved, answer still wrong or missing)
- Q0058 (multi_hop): 'The `--fail-on-refusal` flag turns model refusals into sample errors. The `--retry-refusals` option retries erroring samples. Note that `--retry-refusals` is not a direct flag but can be set on the ag'

### agent_faults: Gave up after a tool timeout (did not retry)
- Q0088 (unanswerable): "I'm unable to retrieve the status of ticket TCK-1500 at this time due to repeated timeouts. I'll try again shortly or we can proceed without this information if needed."
- Q0096 (tool): "I couldn't retrieve the status of ticket TCK-1033 right now. Let's try again later."

### agent_faults: Scorer miss (abstention phrasing)
- Q0077 (unanswerable): "The name of Inspect's built-in vector database for retrieval is not explicitly mentioned in the provided documentation. However, the documentation does discuss a model database used for context window"
- Q0080 (unanswerable): "The default retention period for logs in Inspect's hosted log server is not explicitly stated in the documentation. However, for image logging, by default, inline image and other media bytes are retai"

### agent_faults: Unanswerable mishandled (invented an answer)
- Q0076 (unanswerable): 'Based on the documentation, there is no specific `inspect` command that directly exports an eval log to an Excel workbook. The closest command mentioned is `inspect log export-config`, which exports t'

### agent_faults: Conflict mishandled
- Q0072 (conflicting): 'The default `--retry-wait` between eval-set attempts when `--no-retry-immediate` is set is 10 seconds, according to the documentation [P0564].'
- Q0073 (conflicting): "I don't know."

### agent_faults: Wrong retrieval (no supporting passage retrieved)
- Q0001 (single_hop): 'The environment variable that sets the global default log file format for Inspect is `INSPECT_EVAL_LOG_FORMAT`, which can be configured in your `.env` configuration file. [P0540] [P0445] [P0268] [P029'
- Q0015 (single_hop): "I don't know."
- Q0017 (single_hop): "I don't know."

### agent_faults: Partial retrieval (some supporting passages missing)
- Q0041 (multi_hop): 'The `Dataset` class maps non-standard dataset fields onto samples using the `filter()` method. To shuffle samples, you can use the `--sample-shuffle` option in the CLI or the `sample_shuffle` paramete'
- Q0055 (multi_hop): 'The `response_schema` takes a `ResponseSchema` object, which includes the schema and some additional fields such as the name, description, and strictness. The function that lists the HTTP requests of '

### agent_faults: Evidence ignored (retrieved, answer still wrong or missing)
- Q0058 (multi_hop): 'The `--fail-on-refusal` flag turns model refusals into sample errors. The `--retry-refusals` option retries erroring samples. Note that `--retry-refusals` is not a direct flag but can be set on the ag'

