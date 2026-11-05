"""Turn pinned Inspect AI documentation pages into stable, citable passages.

Passages are split on Markdown headings, then long sections are cut into windows
of at most ``max_words`` words on paragraph boundaries. Passage IDs are assigned
in sorted file order, so the same source commit always yields the same IDs.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from taskbench.schema import Passage

HEADING_RE = re.compile(r"^(#{1,4})\s+(.*?)\s*(\{#[^}]*\})?\s*$")
FRONT_MATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
TITLE_RE = re.compile(r"^title:\s*(.+)$", re.MULTILINE)


def _title(text: str, fallback: str) -> str:
    match = FRONT_MATTER_RE.match(text)
    if match:
        title = TITLE_RE.search(match.group(0))
        if title:
            return title.group(1).strip().strip("\"'")
    return fallback


def _sections(body: str, page_title: str) -> Iterator[tuple[str, str]]:
    """Yield (heading, text) pairs, ignoring headings inside fenced code blocks."""
    heading = page_title
    lines: list[str] = []
    in_code = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        match = None if in_code else HEADING_RE.match(line)
        if match:
            if "\n".join(lines).strip():
                yield heading, "\n".join(lines).strip()
            heading = f"{page_title} > {match.group(2).strip()}"
            lines = []
        else:
            lines.append(line)
    if "\n".join(lines).strip():
        yield heading, "\n".join(lines).strip()


def _windows(text: str, max_words: int) -> Iterator[str]:
    """Split text into chunks of at most ``max_words`` words on blank lines."""
    paragraphs: list[str] = []
    for paragraph in (p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()):
        lines = paragraph.splitlines()
        if len(paragraph.split()) <= max_words or len(lines) == 1:
            paragraphs.append(paragraph)
            continue
        # An oversized block (a long table or code sample): split on line boundaries.
        part: list[str] = []
        for line in lines:
            if part and len(" ".join(part).split()) + len(line.split()) > max_words:
                paragraphs.append("\n".join(part))
                part = []
            part.append(line)
        paragraphs.append("\n".join(part))
    chunk: list[str] = []
    count = 0
    for paragraph in paragraphs:
        words = len(paragraph.split())
        if chunk and count + words > max_words:
            yield "\n\n".join(chunk)
            chunk, count = [], 0
        chunk.append(paragraph)
        count += words
    if chunk:
        yield "\n\n".join(chunk)


def build_passages(
    source_dir: Path,
    source_commit: str,
    license_name: str = "MIT",
    max_words: int = 250,
    min_words: int = 15,
) -> list[Passage]:
    """Build passages from every top-level ``.qmd`` page in ``source_dir``.

    Args:
        source_dir: Directory holding the documentation pages.
        source_commit: Git commit the pages were taken from (recorded on each passage).
        license_name: Licence of the source pages.
        max_words: Upper bound on words per passage.
        min_words: Passages shorter than this are dropped (navigation stubs).

    Returns:
        Passages with sequential IDs ``P0001``, ``P0002``, ...
    """
    pages = sorted(source_dir.glob("*.qmd"))
    if not pages:
        raise FileNotFoundError(f"No .qmd files found in {source_dir}")
    passages: list[Passage] = []
    for page in pages:
        raw = page.read_text(encoding="utf-8")
        title = _title(raw, page.stem)
        body = FRONT_MATTER_RE.sub("", raw, count=1)
        for heading, section in _sections(body, title):
            for chunk in _windows(section, max_words):
                if len(chunk.split()) < min_words:
                    continue
                passages.append(
                    Passage(
                        id=f"P{len(passages) + 1:04d}",
                        source_path=f"docs/{page.name}",
                        source_commit=source_commit,
                        heading=heading,
                        text=chunk,
                        license=license_name,
                    )
                )
    return passages


def write_jsonl(rows: Iterable[Passage], path: Path) -> int:
    """Write passages as JSON lines and return the number written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row.model_dump(), ensure_ascii=False) + "\n")
            n += 1
    return n


def load_passages(path: Path) -> list[Passage]:
    """Load and validate passages from a JSONL file."""
    with path.open(encoding="utf-8") as f:
        return [Passage.model_validate_json(line) for line in f if line.strip()]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build data/passages.jsonl from docs pages.")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--commit", required=True, help="Source git commit hash.")
    parser.add_argument("--out", type=Path, default=Path("data/passages.jsonl"))
    parser.add_argument("--max-words", type=int, default=250)
    args = parser.parse_args(argv)
    passages = build_passages(args.source_dir, args.commit, max_words=args.max_words)
    n = write_jsonl(passages, args.out)
    print(f"Wrote {n} passages to {args.out}")


if __name__ == "__main__":
    main()
