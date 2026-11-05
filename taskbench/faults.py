"""Seeded, reproducible fault injection decisions (no Inspect dependency)."""

from __future__ import annotations

import hashlib


def fault_fires(seed: int, sample_key: str, call_index: int, probability: float) -> bool:
    """Deterministically decide whether one tool call fails.

    The decision depends only on (seed, sample, epoch, call index), so reruns
    inject the same faults and C3/C4 differ only in the faults themselves.
    """
    if probability <= 0:
        return False
    if probability >= 1:
        return True
    digest = hashlib.sha256(f"{seed}:{sample_key}:{call_index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64 < probability
