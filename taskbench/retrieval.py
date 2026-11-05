"""BM25 retrieval over the passage corpus.

BM25 is deliberately simple: it needs no GPU, no embedding model and no vector
database, and it is deterministic, so retrieval is not a source of run-to-run
variance in the benchmark.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from taskbench.schema import Passage

TOKEN_RE = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    """Lower-case word tokens; ``snake_case`` identifiers also yield their parts."""
    tokens: list[str] = []
    for token in TOKEN_RE.findall(text.lower()):
        tokens.append(token)
        if "_" in token:
            tokens.extend(part for part in token.split("_") if part)
    return tokens


@dataclass(frozen=True)
class Hit:
    """A retrieved passage and its BM25 score."""

    passage: Passage
    score: float


class BM25Index:
    """An in-memory BM25 index with deterministic tie-breaking by passage ID."""

    def __init__(self, passages: Sequence[Passage]) -> None:
        if not passages:
            raise ValueError("cannot build an index over zero passages")
        ids = [p.id for p in passages]
        if len(ids) != len(set(ids)):
            raise ValueError("passage IDs must be unique")
        self.passages = list(passages)
        corpus = [tokenize(f"{p.heading}\n{p.text}") for p in self.passages]
        self._bm25 = BM25Okapi(corpus)

    def search(self, query: str, k: int = 5) -> list[Hit]:
        """Return the top ``k`` passages for ``query`` (empty if the query has no tokens)."""
        if k < 1:
            raise ValueError("k must be >= 1")
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            range(len(self.passages)),
            key=lambda i: (-float(scores[i]), self.passages[i].id),
        )
        return [Hit(self.passages[i], float(scores[i])) for i in ranked[:k] if float(scores[i]) > 0]


def format_passages(hits: Sequence[Hit]) -> str:
    """Render hits as labelled context blocks for a prompt."""
    return "\n\n".join(f"[{h.passage.id}] {h.passage.heading}\n{h.passage.text}" for h in hits)
