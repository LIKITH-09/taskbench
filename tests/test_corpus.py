from pathlib import Path

import pytest

from taskbench.corpus import build_passages, load_passages, write_jsonl

PAGE = """---
title: Log Files
---

## Overview

Inspect writes a log for every evaluation run, and the log contains every sample, score and event.

```python
## not a heading inside code
eval("task.py")
```

## Location

The INSPECT_LOG_DIR environment variable overrides the default logs directory used by every run.

## Tiny

Too short.
"""


@pytest.fixture()
def docs(tmp_path: Path) -> Path:
    d = tmp_path / "docs"
    d.mkdir()
    (d / "eval-logs.qmd").write_text(PAGE, encoding="utf-8")
    (d / "a-first.qmd").write_text("# A\n\n" + "word " * 30, encoding="utf-8")
    return d


def test_passages_split_on_headings_not_code(docs: Path):
    passages = build_passages(docs, "abc123", min_words=10)
    headings = [p.heading for p in passages]
    assert "Log Files > Overview" in headings
    assert "Log Files > Location" in headings
    overview = next(p for p in passages if p.heading == "Log Files > Overview")
    assert "## not a heading inside code" in overview.text


def test_short_sections_dropped_and_ids_sequential(docs: Path):
    passages = build_passages(docs, "abc123", min_words=10)
    assert all(p.heading != "Log Files > Tiny" for p in passages)
    assert [p.id for p in passages] == [f"P{i:04d}" for i in range(1, len(passages) + 1)]
    assert passages[0].source_path == "docs/a-first.qmd"  # sorted file order
    assert all(p.source_commit == "abc123" for p in passages)


def test_long_sections_windowed(tmp_path: Path):
    d = tmp_path / "docs"
    d.mkdir()
    body = "\n\n".join("para " + "w " * 60 for _ in range(10))
    (d / "long.qmd").write_text(f"## Long\n\n{body}", encoding="utf-8")
    passages = build_passages(d, "c", max_words=150)
    assert len(passages) > 1
    assert all(len(p.text.split()) <= 150 for p in passages)


def test_roundtrip(docs: Path, tmp_path: Path):
    passages = build_passages(docs, "abc123", min_words=10)
    out = tmp_path / "out.jsonl"
    assert write_jsonl(passages, out) == len(passages)
    assert load_passages(out) == passages
    assert b"\r\n" not in out.read_bytes()


def test_missing_docs_dir(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_passages(tmp_path, "c")
