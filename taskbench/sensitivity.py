"""Post-hoc sensitivity analysis for abstention phrasing on unanswerable tasks.

The frozen scorer (``metrics.is_abstention``) only recognises a few abstention phrases.
Blind human labels on the held-out run showed it missed answers such as "is not
explicitly mentioned in the provided documentation". This module never changes the
frozen scores. It recomputes success for unanswerable rows from the stored answers with a
wider phrase list so the report can show both numbers, labelled as post-hoc.

Deflections such as "I can't check" or "I don't have access" are deliberately NOT counted
as abstentions here, matching how the human labeller marked them.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from taskbench.metrics import is_abstention
from taskbench.schema import ResultRow

EXTRA_ABSTAIN_RE = re.compile(
    r"\b(?:"
    r"(?:is|are|was|were|isn['’]t|aren['’]t|wasn['’]t)\s+(?:not\s+)?"
    r"(?:explicitly\s+|specifically\s+|directly\s+)?(?:mentioned|documented|described|covered|listed)"
    r"|not\s+(?:explicitly\s+|specifically\s+|directly\s+)?(?:mentioned|stated|specified|covered|documented|described|listed)"
    r"|no\s+(?:specific\s+|explicit\s+|such\s+)?\w+\s+(?:is\s+|are\s+)?(?:mentioned|documented|described|listed|provided)"
    r")",
    re.IGNORECASE,
)

# "is mentioned" must not count: the first branch above requires "not" or a negated verb.
_NEGATED_BRANCH = re.compile(r"\b(?:isn['’]t|aren['’]t|wasn['’]t)\b", re.IGNORECASE)


def wide_is_abstention(answer: str) -> bool:
    """Frozen abstention rule, plus 'not (explicitly) mentioned / no specific X mentioned'."""
    if is_abstention(answer):
        return True
    for m in EXTRA_ABSTAIN_RE.finditer(answer):
        text = m.group(0).lower()
        if text.startswith("no ") or "not" in text or _NEGATED_BRANCH.search(text):
            return True
    return False


@dataclass(frozen=True)
class ConfigSensitivity:
    config: str
    unanswerable_rows: int
    strict_success: int
    wide_success: int
    total_rows: int
    total_strict: int
    total_wide: int
    changed: list[ResultRow]


def rescore(rows: Sequence[ResultRow]) -> list[ConfigSensitivity]:
    """Per-config success under the frozen and the wider abstention rule (main condition)."""
    out: list[ConfigSensitivity] = []
    for config in sorted({r.config for r in rows if r.condition == "main"}):
        group = [r for r in rows if r.config == config and r.condition == "main"]
        unans = [r for r in group if r.kind == "unanswerable"]
        changed = [
            r for r in unans if r.status == "success" and not r.success and wide_is_abstention(r.answer)
        ]
        strict = sum(r.success for r in unans)
        out.append(
            ConfigSensitivity(
                config=config,
                unanswerable_rows=len(unans),
                strict_success=strict,
                wide_success=strict + len(changed),
                total_rows=len(group),
                total_strict=sum(r.success for r in group),
                total_wide=sum(r.success for r in group) + len(changed),
                changed=changed,
            )
        )
    return out
