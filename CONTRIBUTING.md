# Contributing

Correctness, reproducibility and honest reporting come first.

1. Open an issue before a substantial change.
2. Add or update tests for every behaviour change; `pytest` and `ruff check .` must pass.
3. Never tune prompts, keywords or scorers on held-out results. If a held-out finding forces a change, bump `PROMPT_VERSION`, document why in `NOTES.md`, and treat earlier held-out runs as superseded.
4. Never commit secrets, real tickets or personal data.
5. Report the commands you actually ran and their real outcomes.
6. Disclose AI assistance in PR descriptions.

```bash
python -m pip install -e ".[dev]"
ruff check . && ruff format --check .
taskbench validate
pytest
```
